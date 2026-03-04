"""Double-dummy interactive hand player views.

Two HTMX endpoints:
  - double_dummy_player_htmx  (GET)  – renders contract selector (or starts
    immediately with the par contract when one is available)
  - double_dummy_play_card_htmx (POST) – processes a card play, calls solver
"""

import copy
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from results.dds_solver import (
    determine_trick_winner,
    hands_to_pbn,
    lho_of,
    next_direction,
    solve_board,
    SUIT_STR_TO_INT,
)
from results.models import ResultsFile
from results.views.core import (
    dealer_and_vulnerability_for_board,
    double_dummy_from_usebio,
)
from results.views.par_contract import par_score_and_contract
from results.views.usebio import parse_usebio_file

# Map full direction names (USEBIO) to single letters
_DIR_FULL_TO_SHORT = {"North": "N", "South": "S", "East": "E", "West": "W"}
# Map full suit names (USEBIO) to short
_SUIT_FULL_TO_SHORT = {"spades": "S", "hearts": "H", "diamonds": "D", "clubs": "C"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _load_hand_for_board(usebio, board_number):
    """Return the hand dict for *board_number* from a parsed USEBIO document.

    Returns a dict keyed by "N"/"E"/"S"/"W", each value a dict keyed by
    "S"/"H"/"D"/"C" with a list of rank characters, e.g.::

        {"N": {"S": ["A","K","4"], "H": ["Q","7"], "D": ["8","5"], "C": ["Q","6","5","4","2"]}, ...}

    Returns None if the board is not found.
    """
    if "HANDSET" not in usebio or "BOARD" not in usebio["HANDSET"]:
        return None

    for board in usebio["HANDSET"]["BOARD"]:
        if int(board["BOARD_NUMBER"]) == board_number:
            hand = {}
            for compass in board["HAND"]:
                direction_short = _DIR_FULL_TO_SHORT.get(compass["DIRECTION"])
                if direction_short is None:
                    continue
                hand[direction_short] = {
                    "S": list(compass.get("SPADES") or ""),
                    "H": list(compass.get("HEARTS") or ""),
                    "D": list(compass.get("DIAMONDS") or ""),
                    "C": list(compass.get("CLUBS") or ""),
                }
            return hand

    return None


def _build_initial_state(hand, trump, declarer, level):
    """Build the initial game-state dict from a hand dict.

    Args:
        hand: dict as returned by _load_hand_for_board
        trump: trump suit string "S"/"H"/"D"/"C"/"N"
        declarer: declarer direction "N"/"E"/"S"/"W"
        level: contract level int 1-7

    Returns:
        game_state dict.
    """
    leader = lho_of(declarer)
    return {
        "trump": trump,
        "declarer": declarer,
        "level": level,
        "trick_leader": leader,
        "next_to_play": leader,
        "tricks_ns": 0,
        "tricks_ew": 0,
        "tricks_sequence": [],
        "current_trick": [],
        "hands": hand,
        "game_over": False,
        "history": [],
    }


def _compute_outcome(solver_score, first, tricks_ns, tricks_ew, declarer, level):
    """Convert a libdds solver score to a contract outcome string.

    Args:
        solver_score: tricks first's side will take in remaining play (from SolveBoardPBN)
        first: direction of player to move ("N"/"E"/"S"/"W")
        tricks_ns: tricks NS has already won
        tricks_ew: tricks EW has already won
        declarer: declarer direction
        level: contract level (1-7)

    Returns:
        outcome string: "+2", "=", "-1" etc.
    """
    if first in ("N", "S"):
        final_ns = tricks_ns + solver_score
    else:
        final_ns = 13 - (tricks_ew + solver_score)

    declarer_tricks = final_ns if declarer in ("N", "S") else 13 - final_ns
    outcome = declarer_tricks - (level + 6)

    if outcome > 0:
        return f"+{outcome}"
    elif outcome == 0:
        return "="
    else:
        return str(outcome)


def _get_legal_cards(hand_for_player, led_suit):
    """Return legal cards for *hand_for_player* given the current *led_suit*.

    Args:
        hand_for_player: dict keyed "S"/"H"/"D"/"C", values are lists of rank chars.
        led_suit: suit string "S"/"H"/"D"/"C" or None (trick not yet started).

    Returns:
        dict of same shape but containing only legal cards to play.
    """
    if led_suit and hand_for_player.get(led_suit):
        # Must follow suit
        return {led_suit: hand_for_player[led_suit]}
    # No restriction
    return {s: list(cards) for s, cards in hand_for_player.items()}


def _build_trick_arrays(current_trick):
    """Convert current_trick list to (trick_suits, trick_ranks) for SolveBoardPBN."""
    trick_suits = [SUIT_STR_TO_INT.get(c["suit"], 0) for c in current_trick]
    trick_ranks = [
        {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "T": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14,
        }.get(c["rank"], 0)
        for c in current_trick
    ]
    return trick_suits, trick_ranks


def _parse_par_contract(par_string):
    """Extract (level, trump, declarer, double) from a par_string.

    Handles formats like:
      "4N= by N for 430"
      "5HX by EW for 100"
      "4S= by N or 4H= by E for -620"   ← takes first contract

    Returns (level_int, trump_str, declarer_str, double_str) or
    (None, None, None, None) on failure.
    """
    if not par_string:
        return None, None, None, None
    try:
        first = par_string.split(" or ")[0].strip()
        level = int(first[0])
        trump = first[1]  # C/D/H/S/N
        suffix = first[2:]  # e.g. "X by EW for 100" or "= by N for 430"
        double = (
            "XX" if suffix.startswith("XX") else "X" if suffix.startswith("X") else ""
        )
        by_idx = first.find(" by ")
        if by_idx < 0:
            return None, None, None, None
        declarer_raw = first[by_idx + 4 :].split()[0]
        declarer = {"NS": "N", "EW": "E"}.get(declarer_raw, declarer_raw)
        if declarer not in ("N", "E", "S", "W"):
            return None, None, None, None
        return level, trump, declarer, double
    except (IndexError, ValueError, AttributeError):
        return None, None, None, None


def _render_player(request, state, results_file_id, board_number, trick_pause=False):
    """Run solver calls and render the player.html fragment."""
    next_player = state["next_to_play"]
    led_suit_now = state["current_trick"][0]["suit"] if state["current_trick"] else None
    level = state.get("level", 1)

    solver_cards = []
    active_outcomes = {}

    if not state["game_over"] and not trick_pause:
        pbn = hands_to_pbn(state["hands"])
        trick_suits, trick_ranks = _build_trick_arrays(state["current_trick"])

        solver_cards = solve_board(
            pbn, state["trump"], state["trick_leader"], trick_suits, trick_ranks
        )
        active_outcomes = {
            (sc["suit"], sc["rank"]): _compute_outcome(
                sc["score"],
                next_player,
                state["tricks_ns"],
                state["tricks_ew"],
                state["declarer"],
                level,
            )
            for sc in solver_cards
        }

    is_optimal_set = {
        (sc["suit"], sc["rank"]) for sc in solver_cards if sc["is_optimal"]
    }

    if not state["game_over"] and not trick_pause:
        legal_cards = _get_legal_cards(state["hands"][next_player], led_suit_now)
    else:
        legal_cards = {}

    game_state_json = json.dumps(state)

    _suit_meta = [
        ("S", "♠", "black"),
        ("H", "♥", "red"),
        ("D", "♦", "red"),
        ("C", "♣", "black"),
    ]
    rendered_hands = {}
    for dir_key in ["N", "E", "S", "W"]:
        suits = []
        dir_outcomes = active_outcomes if dir_key == next_player else {}
        for suit_key, symbol, color in _suit_meta:
            cards = []
            for rank in state["hands"][dir_key].get(suit_key, []):
                is_active = (
                    not trick_pause
                    and (dir_key == next_player)
                    and not state["game_over"]
                )
                is_legal = is_active and (
                    suit_key in legal_cards and rank in legal_cards[suit_key]
                )
                is_optimal = (
                    is_active and is_legal and (suit_key, rank) in is_optimal_set
                )
                outcome = dir_outcomes.get((suit_key, rank), "")
                cards.append(
                    {
                        "rank": rank,
                        "is_active": is_active,
                        "is_legal": is_legal,
                        "is_optimal": is_optimal,
                        "outcome": outcome,
                        "outcome_positive": bool(outcome)
                        and (outcome == "=" or outcome[0] == "+"),
                    }
                )
            suits.append(
                {"key": suit_key, "symbol": symbol, "color": color, "cards": cards}
            )
        rendered_hands[dir_key] = suits

    trick_by_dir = {tc["direction"]: tc for tc in state["current_trick"]}

    # Pre-compute absolute left positions for the trick pile so each card
    # is offset by a fixed 4 px regardless of portrait vs landscape width.
    _peek = 6  # px each card peeks out to the right of the previous
    tricks_display = [
        {"side": side, "left_px": i * _peek}
        for i, side in enumerate(state.get("tricks_sequence", []))
    ]
    if tricks_display:
        last_width = 48 if tricks_display[-1]["side"] == "EW" else 34
        pile_width = tricks_display[-1]["left_px"] + last_width
    else:
        pile_width = 0

    return render(
        request,
        "results/double_dummy/player.html",
        {
            "state": state,
            "game_state_json": game_state_json,
            "rendered_hands": rendered_hands,
            "trick_by_dir": trick_by_dir,
            "results_file_id": results_file_id,
            "board_number": board_number,
            "directions": ["N", "E", "S", "W"],
            "tricks_display": tricks_display,
            "pile_width": pile_width,
            "trick_pause": trick_pause,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────────────────────────────────────


@login_required()
def double_dummy_player_htmx(request, results_file_id, board_number):
    """GET – start playing immediately with the par contract, or show contract selector.

    Pass ?setup=1 to force the contract selector (e.g. from the "Change contract" button).
    """
    results_file = get_object_or_404(ResultsFile, pk=results_file_id)
    usebio = parse_usebio_file(results_file)

    hand = _load_hand_for_board(usebio, board_number)
    if hand is None:
        return HttpResponse(
            f"<p class='text-danger'>Board {board_number} hand data not found.</p>"
        )

    dealer, vulnerability = dealer_and_vulnerability_for_board(board_number)

    preselect_level = preselect_trump = preselect_declarer = None
    try:
        for board in usebio["HANDSET"]["BOARD"]:
            if int(board["BOARD_NUMBER"]) == board_number:
                dd_table = double_dummy_from_usebio(board["HAND"])
                _, par_string = par_score_and_contract(dd_table, vulnerability, dealer)
                (
                    preselect_level,
                    preselect_trump,
                    preselect_declarer,
                    preselect_double,
                ) = _parse_par_contract(par_string)
                break
    except Exception:
        pass

    if not request.GET.get("setup"):
        # Prefer a contract passed explicitly via query params (e.g. the pair's
        # actual contract from the board detail view) over the par contract.
        qs_level = request.GET.get("level")
        qs_trump = request.GET.get("trump")
        qs_declarer = request.GET.get("declarer")
        qs_double = request.GET.get("double", "")
        try:
            qs_level_int = int(qs_level) if qs_level else None
        except (ValueError, TypeError):
            qs_level_int = None

        if (
            qs_level_int
            and 1 <= qs_level_int <= 7
            and qs_trump in ("S", "H", "D", "C", "N")
            and qs_declarer in ("N", "E", "S", "W")
        ):
            state = _build_initial_state(hand, qs_trump, qs_declarer, qs_level_int)
            state["double"] = qs_double if qs_double in ("X", "XX") else ""
            return _render_player(request, state, results_file_id, board_number)

        # Fall back to the par contract
        if preselect_level:
            state = _build_initial_state(
                hand, preselect_trump, preselect_declarer, preselect_level
            )
            state["is_par_contract"] = True
            state["double"] = preselect_double or ""
            return _render_player(request, state, results_file_id, board_number)

    # Fallback: show the contract selector
    trumps = [
        ("S", "♠", "black"),
        ("H", "♥", "red"),
        ("D", "♦", "red"),
        ("C", "♣", "black"),
    ]

    return render(
        request,
        "results/double_dummy/setup.html",
        {
            "results_file_id": results_file_id,
            "board_number": board_number,
            "dealer": dealer,
            "vulnerability": vulnerability,
            "trumps": trumps,
            "levels": list(range(1, 8)),
            "declarer_dirs": ["N", "E", "S", "W"],
            "preselect_level": preselect_level,
            "preselect_trump": preselect_trump,
            "preselect_declarer": preselect_declarer,
        },
    )


@login_required()
def double_dummy_play_card_htmx(request, results_file_id, board_number):
    """POST – process a card play (or initial Start) and return updated player fragment."""

    if request.method != "POST":
        return HttpResponse(status=405)

    # ── Parse or build game state ──────────────────────────────────────────
    raw_state = request.POST.get("game_state", "")
    played_suit = request.POST.get("played_suit", "")
    played_rank = request.POST.get("played_rank", "")
    action = request.POST.get("action", "")

    if raw_state:
        try:
            state = json.loads(raw_state)
        except (json.JSONDecodeError, ValueError):
            return HttpResponse(
                "<p class='text-danger'>Invalid game state.</p>", status=400
            )
    else:
        # Initial start — build state from USEBIO + form params
        trump = request.POST.get("trump", "N")
        declarer = request.POST.get("declarer", "N")
        try:
            level = max(1, min(7, int(request.POST.get("level", "1"))))
        except (ValueError, TypeError):
            level = 1

        results_file = get_object_or_404(ResultsFile, pk=results_file_id)
        usebio = parse_usebio_file(results_file)
        hand = _load_hand_for_board(usebio, board_number)
        if hand is None:
            return HttpResponse(
                f"<p class='text-danger'>Board {board_number} hand data not found.</p>"
            )
        state = _build_initial_state(hand, trump, declarer, level)

    # ── Complete trick after pause ─────────────────────────────────────────
    if action == "complete_trick":
        if len(state.get("current_trick", [])) == 4:
            winner = determine_trick_winner(state["current_trick"], state["trump"])
            if winner in ("N", "S"):
                state["tricks_ns"] += 1
                state.setdefault("tricks_sequence", []).append("NS")
            else:
                state["tricks_ew"] += 1
                state.setdefault("tricks_sequence", []).append("EW")
            state.setdefault("trick_history", []).append(list(state["current_trick"]))
            state["current_trick"] = []
            state["trick_leader"] = winner
            state["next_to_play"] = winner
        # fall through to game_over check and render

    # ── Undo actions ───────────────────────────────────────────────────────
    elif action in ("undo_one", "undo_all"):
        history = state.get("history", [])
        if history:
            if action == "undo_all":
                restored = history[0]
                restored["history"] = []
            else:
                restored = history[-1]
                restored["history"] = history[:-1]
            return _render_player(request, restored, results_file_id, board_number)
        return _render_player(request, state, results_file_id, board_number)

    # ── Process played card (if any) ───────────────────────────────────────
    if played_suit and played_rank and not state.get("game_over"):
        current_player = state["next_to_play"]
        player_hand = state["hands"][current_player]

        # Validate card is in hand
        if played_rank not in player_hand.get(played_suit, []):
            return HttpResponse(
                "<p class='text-danger'>Illegal card — not in your hand.</p>",
                status=400,
            )

        # Validate follow-suit rule
        led_suit = state["current_trick"][0]["suit"] if state["current_trick"] else None
        legal = _get_legal_cards(player_hand, led_suit)
        if played_suit not in legal or played_rank not in legal[played_suit]:
            return HttpResponse(
                "<p class='text-danger'>Illegal card — must follow suit.</p>",
                status=400,
            )

        # Snapshot state before mutation so undo can restore it
        snapshot = copy.deepcopy({k: v for k, v in state.items() if k != "history"})
        state.setdefault("history", []).append(snapshot)

        # Remove card from hand
        player_hand[played_suit].remove(played_rank)

        # Add to current trick
        state["current_trick"].append(
            {"direction": current_player, "suit": played_suit, "rank": played_rank}
        )

        # Check trick completion
        if len(state["current_trick"]) == 4:
            # Pause briefly so the user can see all 4 cards before clearing
            return _render_player(
                request, state, results_file_id, board_number, trick_pause=True
            )
        else:
            state["next_to_play"] = next_direction(current_player)

    # ── Check for game over ────────────────────────────────────────────────
    total_tricks = state["tricks_ns"] + state["tricks_ew"]
    if total_tricks == 13:
        state["game_over"] = True

    return _render_player(request, state, results_file_id, board_number)
