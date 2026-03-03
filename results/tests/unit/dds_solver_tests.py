"""Unit tests for results/dds_solver.py helper functions."""

from results.dds_solver import determine_trick_winner, hands_to_pbn
from results.views.double_dummy_player import _get_legal_cards
from tests.test_manager import CobaltTestManagerUnit


class DDSSolverTests:
    """Unit tests for the double-dummy solver helper functions."""

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager

    # ── determine_trick_winner ────────────────────────────────────────────

    def test_trick_winner_led_suit_wins(self):
        """Highest card in the led suit wins when no trumps played."""

        trick = [
            {"direction": "W", "suit": "S", "rank": "9"},
            {"direction": "N", "suit": "S", "rank": "K"},
            {"direction": "E", "suit": "S", "rank": "Q"},
            {"direction": "S", "suit": "S", "rank": "J"},
        ]
        result = determine_trick_winner(trick, "H")
        self.manager.save_results(
            status=result == "N",
            test_name="Trick winner — led suit",
            test_description="K of spades beats 9, Q, J when trump is hearts.",
            output=f"Expected N, got {result}",
        )

    def test_trick_winner_trump_beats_led_suit(self):
        """A trump beats a higher card in the led suit."""

        trick = [
            {"direction": "N", "suit": "S", "rank": "A"},
            {"direction": "E", "suit": "H", "rank": "2"},
            {"direction": "S", "suit": "S", "rank": "K"},
            {"direction": "W", "suit": "S", "rank": "Q"},
        ]
        result = determine_trick_winner(trick, "H")
        self.manager.save_results(
            status=result == "E",
            test_name="Trick winner — trump overruffs",
            test_description="2 of hearts (trump) beats A/K/Q of spades.",
            output=f"Expected E, got {result}",
        )

    def test_trick_winner_highest_trump(self):
        """When multiple trumps are played, highest wins."""

        trick = [
            {"direction": "N", "suit": "S", "rank": "A"},
            {"direction": "E", "suit": "H", "rank": "2"},
            {"direction": "S", "suit": "H", "rank": "A"},
            {"direction": "W", "suit": "H", "rank": "K"},
        ]
        result = determine_trick_winner(trick, "H")
        self.manager.save_results(
            status=result == "S",
            test_name="Trick winner — highest trump",
            test_description="Ace of hearts beats king and 2 of hearts.",
            output=f"Expected S, got {result}",
        )

    def test_trick_winner_discard_cannot_win(self):
        """A discard in a non-led, non-trump suit cannot win."""

        trick = [
            {"direction": "W", "suit": "C", "rank": "5"},
            {"direction": "N", "suit": "D", "rank": "A"},  # off-suit discard
            {"direction": "E", "suit": "C", "rank": "3"},
            {"direction": "S", "suit": "C", "rank": "8"},
        ]
        result = determine_trick_winner(trick, "H")
        self.manager.save_results(
            status=result == "S",
            test_name="Trick winner — discard cannot win",
            test_description="Ace of diamonds discard cannot beat 8 of clubs (led suit).",
            output=f"Expected S, got {result}",
        )

    def test_trick_winner_nt_no_trump(self):
        """In NT the highest card of the led suit wins regardless of other suits."""

        trick = [
            {"direction": "N", "suit": "H", "rank": "4"},
            {"direction": "E", "suit": "S", "rank": "A"},  # discard, can't win
            {"direction": "S", "suit": "H", "rank": "K"},
            {"direction": "W", "suit": "H", "rank": "Q"},
        ]
        result = determine_trick_winner(trick, "N")
        self.manager.save_results(
            status=result == "S",
            test_name="Trick winner — NT",
            test_description="King of hearts wins over queen and 4; ace of spades is a discard.",
            output=f"Expected S, got {result}",
        )

    # ── hands_to_pbn ──────────────────────────────────────────────────────

    def test_hands_to_pbn_full_hand(self):
        """hands_to_pbn builds the correct PBN string for a known hand."""

        hands = {
            "N": {
                "S": ["A", "K", "4", "3", "2"],
                "H": ["Q", "7"],
                "D": ["8", "5"],
                "C": ["Q", "6", "5", "4", "2"],
            },
            "E": {
                "S": ["Q", "J", "T", "9"],
                "H": ["A", "K", "J", "T", "9"],
                "D": ["T", "9", "7", "4"],
                "C": ["3"],
            },
            "S": {
                "S": ["8", "7", "6", "5"],
                "H": ["8", "6", "5"],
                "D": ["A", "K", "Q", "J", "6", "3"],
                "C": ["8"],
            },
            "W": {
                "S": ["3"],
                "H": ["4", "3", "2"],
                "D": ["2"],
                "C": ["A", "K", "J", "T", "9", "7"],
            },
        }
        result = hands_to_pbn(hands)
        expected = (
            "N:AK432.Q7.85.Q6542 "
            "QJT9.AKJT9.T974.3 "
            "8765.865.AKQJ63.8 "
            "3.432.2.AKJT97"
        )
        self.manager.save_results(
            status=result == expected,
            test_name="hands_to_pbn — full hand",
            test_description="PBN string construction matches expected format.",
            output=f"Expected:\n{expected}\nGot:\n{result}",
        )

    def test_hands_to_pbn_void_suit(self):
        """hands_to_pbn handles a void suit as an empty segment (two adjacent dots)."""

        hands = {
            "N": {"S": ["A"], "H": [], "D": ["K"], "C": ["Q"]},
            "E": {"S": [], "H": ["A"], "D": ["K"], "C": ["Q"]},
            "S": {"S": ["A"], "H": ["K"], "D": [], "C": ["Q"]},
            "W": {"S": ["A"], "H": ["K"], "D": ["Q"], "C": []},
        }
        result = hands_to_pbn(hands)
        # N has void hearts → "A..K.Q"
        self.manager.save_results(
            status=result.startswith("N:A..K.Q"),
            test_name="hands_to_pbn — void suit",
            test_description="Void suit renders as empty string between dots.",
            output=f"Result: {result}",
        )

    # ── _get_legal_cards ──────────────────────────────────────────────────

    def test_legal_cards_follow_suit(self):
        """When led suit matches cards in hand, only those cards are returned."""

        hand = {"S": ["A", "K"], "H": ["Q", "J"], "D": [], "C": ["5"]}
        result = _get_legal_cards(hand, "S")
        self.manager.save_results(
            status=result == {"S": ["A", "K"]},
            test_name="_get_legal_cards — follow suit",
            test_description="Must follow spades when spades are led and player has spades.",
            output=f"Expected {{'S': ['A', 'K']}}, got {result}",
        )

    def test_legal_cards_void_in_led_suit(self):
        """When player is void in the led suit, all cards are legal."""

        hand = {"S": [], "H": ["Q", "J"], "D": ["A"], "C": ["5"]}
        result = _get_legal_cards(hand, "S")
        # All cards should be returned (void in spades)
        all_cards = {"S": [], "H": ["Q", "J"], "D": ["A"], "C": ["5"]}
        self.manager.save_results(
            status=result == all_cards,
            test_name="_get_legal_cards — void in led suit",
            test_description="Void in led suit means all cards are legal.",
            output=f"Expected {all_cards}, got {result}",
        )

    def test_legal_cards_no_led_suit(self):
        """When no led suit (first to play), all cards are legal."""

        hand = {"S": ["A"], "H": ["K"], "D": ["Q"], "C": ["J"]}
        result = _get_legal_cards(hand, None)
        self.manager.save_results(
            status=result == hand,
            test_name="_get_legal_cards — no led suit",
            test_description="When trick is empty (no led suit), any card is legal.",
            output=f"Expected {hand}, got {result}",
        )
