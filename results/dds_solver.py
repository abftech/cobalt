"""DDS (Double Dummy Solver) integration via SolveBoardPBN from libdds.

This module extends the ctypes bindings already established in ddstable to expose
SolveBoardPBN for single-position solving (finding optimal cards to play next).
"""

import ctypes
from ctypes import Structure, byref, c_char, c_int

try:
    from ddstable import ddstable

    dll = ddstable.dll
except (ImportError, OSError, AttributeError):
    dll = None

# ── Suit / direction / rank conversion tables ──────────────────────────────────
# libdds conventions: suit 0=S 1=H 2=D 3=C 4=NT; direction 0=N 1=E 2=S 3=W
SUIT_STR_TO_INT = {"S": 0, "H": 1, "D": 2, "C": 3, "N": 4}
SUIT_INT_TO_STR = {0: "S", 1: "H", 2: "D", 3: "C", 4: "N"}

DIR_STR_TO_INT = {"N": 0, "E": 1, "S": 2, "W": 3}
DIR_INT_TO_STR = {0: "N", 1: "E", 2: "S", 3: "W"}

RANK_STR_TO_INT = {
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
}
RANK_INT_TO_STR = {v: k for k, v in RANK_STR_TO_INT.items()}

# Rotation order for direction cycling
_ROTATION = ["N", "E", "S", "W"]


def next_direction(direction):
    """Return the next direction in clockwise rotation (N→E→S→W→N)."""
    return _ROTATION[(_ROTATION.index(direction) + 1) % 4]


def lho_of(direction):
    """Return the Left Hand Opponent of *direction* (next clockwise player)."""
    return next_direction(direction)


# ── ctypes structures for SolveBoardPBN ───────────────────────────────────────


class _DealPBN(Structure):
    _fields_ = [
        ("trump", c_int),
        ("first", c_int),
        ("currentTrickSuit", c_int * 3),
        ("currentTrickRank", c_int * 3),
        ("remainCards", c_char * 80),
    ]


class _FutureTricks(Structure):
    _fields_ = [
        ("nodes", c_int),
        ("cards", c_int),
        ("suit", c_int * 13),
        ("rank", c_int * 13),
        ("equals", c_int * 13),
        ("score", c_int * 13),
    ]


# ── Public API ─────────────────────────────────────────────────────────────────


def hands_to_pbn(hands):
    """Convert internal hands dict to a PBN string suitable for remainCards.

    Args:
        hands: dict keyed by "N"/"E"/"S"/"W", each value a dict keyed by
               "S"/"H"/"D"/"C" with list-of-rank-chars values, e.g.
               {"N": {"S": ["A","K"], "H": ["Q"], "D": [], "C": ["5","4","3","2"]}, ...}

    Returns:
        PBN string: "N:S.H.D.C E:... S:... W:..."
        Voids are represented as empty strings between dots (e.g. "AK..85.Q65").
    """
    parts = []
    for direction in ["N", "E", "S", "W"]:
        hand = hands[direction]
        spades = "".join(hand.get("S", []))
        hearts = "".join(hand.get("H", []))
        diamonds = "".join(hand.get("D", []))
        clubs = "".join(hand.get("C", []))
        parts.append(f"{spades}.{hearts}.{diamonds}.{clubs}")
    return "N:" + " ".join(parts)


def solve_board(
    remaining_pbn, trump_str, first_str, trick_suits=None, trick_ranks=None
):
    """Call SolveBoardPBN to find the optimal card(s) to play.

    Args:
        remaining_pbn (str): PBN string for remaining cards (from hands_to_pbn).
        trump_str (str): trump suit as "S"/"H"/"D"/"C"/"N" (NT).
        first_str (str): direction of player to move as "N"/"E"/"S"/"W".
        trick_suits (list[int]|None): suits of cards already played in current
            trick (0–3 each), length 0–3. None means empty trick.
        trick_ranks (list[int]|None): ranks of cards already played in current
            trick (2–14 each), length 0–3.

    Returns:
        list[dict]: each dict has keys "suit" (str), "rank" (str), "score" (int).
        Returns [] on error.
    """
    if dll is None:
        return []

    trump_int = SUIT_STR_TO_INT.get(trump_str, 4)
    first_int = DIR_STR_TO_INT.get(first_str, 0)

    deal = _DealPBN()
    deal.trump = trump_int
    deal.first = first_int

    # Fill current-trick arrays (pad with 0s)
    trick_suits = trick_suits or []
    trick_ranks = trick_ranks or []
    for i in range(3):
        deal.currentTrickSuit[i] = trick_suits[i] if i < len(trick_suits) else 0
        deal.currentTrickRank[i] = trick_ranks[i] if i < len(trick_ranks) else 0

    pbn_bytes = remaining_pbn.encode("utf-8")
    deal.remainCards = pbn_bytes

    fut = _FutureTricks()

    try:
        res = dll.SolveBoardPBN(deal, -1, 2, 1, byref(fut), 0)
    except Exception:
        return []

    if res != 1:
        return []

    results = []
    max_score = None
    for i in range(fut.cards):
        score = fut.score[i]
        suit = SUIT_INT_TO_STR.get(fut.suit[i], "?")
        rank = RANK_INT_TO_STR.get(fut.rank[i], "?")
        if max_score is None:
            max_score = score
        # solutions=2 returns cards tied for best score; include all with max score
        if score == max_score:
            results.append({"suit": suit, "rank": rank, "score": score})
    return results


def determine_trick_winner(trick_cards, trump_str):
    """Determine the winner of a completed trick.

    Args:
        trick_cards: list of 4 dicts, each {"direction": str, "suit": str, "rank": str},
                     in play order (leader first).
        trump_str: trump suit as "S"/"H"/"D"/"C"/"N" ("N" = no trumps).

    Returns:
        Winning direction as "N"/"E"/"S"/"W".
    """
    if not trick_cards:
        return trick_cards[0]["direction"]

    led_suit = trick_cards[0]["suit"]
    winning_card = trick_cards[0]

    for card in trick_cards[1:]:
        current_winner_suit = winning_card["suit"]
        current_winner_rank = RANK_STR_TO_INT[winning_card["rank"]]
        challenger_suit = card["suit"]
        challenger_rank = RANK_STR_TO_INT[card["rank"]]

        if current_winner_suit == trump_str:
            # Current winner is a trump — only a higher trump beats it
            if challenger_suit == trump_str and challenger_rank > current_winner_rank:
                winning_card = card
        elif challenger_suit == trump_str:
            # Challenger trumped a non-trump winner
            winning_card = card
        elif challenger_suit == led_suit and challenger_rank > current_winner_rank:
            # Both in led suit; challenger is higher
            winning_card = card
        # else: challenger is a non-trump discard in a different suit — can't win

    return winning_card["direction"]
