from types import SimpleNamespace

from ddstable import ddstable
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from results.models import PlayerSummaryResult


@login_required
def home(request):
    return render(request, "results/home.html")


def get_recent_results(user):
    """Return the 5 most recent results for a user. Called by Dashboard"""

    return PlayerSummaryResult.objects.filter(
        player_system_number=user.system_number
    ).order_by("result_date")[:5]


def double_dummy_from_usebio(board):
    """perform a double dummy analysis of a hand.
    This requires libdds.so to be available on the path. See the documentation
    if you need to rebuild this for your OS. It works fine on Linux out of the box. Nothing extra required,
    just pip install ddstable.

    We expect to get part of the USEBIO XML - ['USEBIO']["HANDSET"]["BOARD"][?]

    Data contains a list with direction and suits ('DIRECTION', 'East'), ('CLUBS', 'Q6542'), ('DIAMONDS', '85'),...

    """

    # Build PBN format string

    hand = {}

    print(board)

    for compass in board:
        hand[compass["DIRECTION"]] = {}
        hand[compass["DIRECTION"]]["clubs"] = compass["CLUBS"]
        hand[compass["DIRECTION"]]["diamonds"] = compass["DIAMONDS"]
        hand[compass["DIRECTION"]]["hearts"] = compass["HEARTS"]
        hand[compass["DIRECTION"]]["spades"] = compass["SPADES"]

    print(hand)

    pbn_str = f"E:{hand['North']['spades']}.{hand['North']['hearts']}.{hand['North']['diamonds']}.{hand['North']['clubs']}"
    pbn_str += f" {hand['East']['spades']}.{hand['East']['hearts']}.{hand['East']['diamonds']}.{hand['East']['clubs']}"
    pbn_str += f" {hand['South']['spades']}.{hand['South']['hearts']}.{hand['South']['diamonds']}.{hand['South']['clubs']}"
    pbn_str += f" {hand['West']['spades']}.{hand['West']['hearts']}.{hand['West']['diamonds']}.{hand['West']['clubs']}"

    pbn_bytes = bytes(pbn_str, encoding="utf-8")

    # PBN = b"E:QJT5432.T.6.QJ82 .J97543.K7532.94 87.A62.QJT4.AT75 AK96.KQ8.A98.K63"
    all = ddstable.get_ddstable(pbn_bytes)
    print(all)

    return all


def _score_for_contract_static(contract, vulnerability, declarer):
    """set up static data for this session"""

    # Breakdown the contract
    tricks_committed = int(contract[0]) + 6
    denomination = contract[1]
    if contract[2:] == "XX":
        redoubled = True
        doubled = False
        factor = 4
    elif contract[2:] == "X":
        redoubled = False
        doubled = True
        factor = 2
    else:
        redoubled = False
        doubled = False
        factor = 0

    # Set vulnerable
    is_vulnerable = bool(declarer in ["N", "S"] and vulnerability in ["NS", "ALL"]) or (
        declarer in ["E", "W"] and vulnerability in ["EW", "ALL"]
    )

    # use part score bonus (50) as starting point
    starting_making_score = 50

    # For NT add on the 10 for the first trick
    if denomination == "N":
        starting_making_score += 10

    # Set bonuses and overtricks
    if is_vulnerable:
        # Vul
        game_bonus = 450  # 500, but we already gave 50
        slam_bonus = 1200  # 750 + 500 for game but we already gave 50
        grand_slam_bonus = 1950  # 1500 + 500 for game but we already gave 50
        doubled_over_trick_value = 200
        redoubled_over_trick_value = 400
        under_trick_value = 100
    else:
        # Non-Vul
        game_bonus = 250  # 300, but we already gave 50
        slam_bonus = 750  # 500 + 300 for game, but we already gave 50
        grand_slam_bonus = 1250  # 1000 + 300 for game, but we already gave 50
        doubled_over_trick_value = 100
        redoubled_over_trick_value = 200
        under_trick_value = 50

    score_per_trick = 20 if denomination in ["C", "D"] else 30

    data = {
        "starting_making_score": starting_making_score,
        "game_bonus": game_bonus,
        "slam_bonus": slam_bonus,
        "grand_slam_bonus": grand_slam_bonus,
        "is_vulnerable": is_vulnerable,
        "tricks_committed": tricks_committed,
        "denomination": denomination,
        "doubled": doubled,
        "redoubled": redoubled,
        "score_per_trick": score_per_trick,
        "doubled_over_trick_value": doubled_over_trick_value,
        "redoubled_over_trick_value": redoubled_over_trick_value,
        "under_trick_value": under_trick_value,
        "factor": factor,
    }

    # return as a dotable thing. Pretty cool.
    return SimpleNamespace(**data)


def _score_for_contract_add_bonus(static, tricks_taken, score):
    """sub to calculate bonuses

    For doubled contracts we will get the tricks_taken and tricks_committed as doubled values
    which could be greater than 13

    """
    print("tricks_taken", tricks_taken)
    print("static.tricks_committed", static.tricks_committed)
    print("score", score)

    # Grand slam
    if tricks_taken >= 13 and static.tricks_committed >= 13:
        score += static.grand_slam_bonus

    # small slam
    elif tricks_taken >= 12 and static.tricks_committed >= 12:
        score += static.slam_bonus

    # game
    elif (
        (static.denomination in ["C", "D"] and static.tricks_committed >= 11)
        or (static.denomination in ["H", "S"] and static.tricks_committed >= 10)
        or (static.denomination == "N" and static.tricks_committed >= 9)
    ):
        score += static.game_bonus

    print("bonus", score)
    return score


def _score_for_contract_making(static, tricks_taken):
    """sub for making contracts"""

    # handle doubled and redoubled making
    if static.doubled or static.redoubled:

        if static.doubled:
            over_trick_value = static.doubled_over_trick_value
            insult = 50
        else:
            over_trick_value = static.redoubled_over_trick_value
            insult = 100

        # also double the tricks made for the bonus calculation
        # calculate over tricks for further down e.g. 2Hx making 9 is 9-6 - 8-6 = 1
        over_tricks = (tricks_taken - 6) - (static.tricks_committed - 6)
        tricks_taken = 6 + ((static.tricks_committed - 6) * static.factor)
        actual_tricks_committed = static.tricks_committed

        # You can only be doubled into game not a slam
        if static.tricks_committed <= 12 and tricks_taken <= 12:
            static.tricks_committed = tricks_taken

        # score for bonus calculations excludes over tricks, we add them later
        score = (
            (actual_tricks_committed - 6) * static.score_per_trick * static.factor
        ) + static.starting_making_score

        # for NT we need to adjust
        if static.denomination == "N":
            score = (
                (actual_tricks_committed - 6)
                * (static.score_per_trick + 10)
                * static.factor
            ) + 50

        print("static.tricks_committed pretend", static.tricks_committed)
        print("tricks_taken pretend", tricks_taken)
        print("static.score_per_trick", static.score_per_trick)
        print("static.starting_making_score", static.starting_making_score)
        print("score after double", score)
        print("over tricks", over_tricks)

    else:  # not doubled
        # starting score = score for tricks + base score (part score)
        score = (
            (tricks_taken - 6) * static.score_per_trick
        ) + static.starting_making_score

    # add bonuses if appropriate
    score = _score_for_contract_add_bonus(static, tricks_taken, score)

    # handle over tricks and insult
    if static.doubled or static.redoubled:
        print("over_tricks", over_tricks)
        print("over_tricks_value", over_trick_value)
        print("Score before over tricks", score)

        # add to score and add the insult
        score += (over_tricks * over_trick_value) + insult

        print("Score after over tricks", score)

    return score


def _score_for_contract_failing(static, tricks_taken):
    """sub for contracts going off"""

    under_tricks = static.tricks_committed - tricks_taken
    if static.doubled or static.redoubled:
        if static.is_vulnerable and static.doubled:
            penalties = [
                200,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
            ]
        if static.is_vulnerable and static.redoubled:
            penalties = [
                400,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
            ]
        if not static.is_vulnerable and static.doubled:
            penalties = [
                100,
                200,
                200,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
                300,
            ]
        if not static.is_vulnerable and static.redoubled:
            penalties = [
                200,
                400,
                400,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
                600,
            ]

        score = 0
        index = 0
        while under_tricks > 0:
            score += penalties[index]
            index += 1
            under_tricks -= 1

    else:
        # not doubled
        score = static.under_trick_value * under_tricks

    return score


def score_for_contract(contract, vulnerability, declarer, tricks_taken):
    """Calculate the score for any contract

    args:

        contract(str): contract in the form NCD where N is a number 1-7, C is a letter (C/D/H/S/N) and D can be X or XX
        vulnerability(str): vulnerability for this board
        declarer(str): N/S/E/W
        tricks_taken(int): 0-13

    """

    # Get static for this session
    static = _score_for_contract_static(contract, vulnerability, declarer)

    # Making contracts
    if tricks_taken >= static.tricks_committed:
        return _score_for_contract_making(static, tricks_taken)

    # Non-making contracts
    else:
        return _score_for_contract_failing(static, tricks_taken)
