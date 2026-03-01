"""
Pytest version of 01_user_event_entry.py

Tests event entry through the UI using Selenium against a running Django server.

Requirements (not yet in requirements.txt):
    pytest
    pytest-django

Run with:
    pytest events/tests/integration/test_user_event_entry.py \
        --ds=cobalt.settings -v

The server must be running at BASE_URL with test data already seeded
(python manage.py add_test_data). Test users have system numbers 110-115
and password F1shcake.
"""

import os
from time import sleep

import pytest
from django.urls import reverse
from post_office.models import Email
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from accounts.models import TeamMate, User
from events.models import Congress, Event, EventEntryPlayer
from payments.models import MemberTransaction, OrganisationTransaction
from payments.views.core import get_balance, update_account


BASE_URL = os.environ.get("COBALT_TEST_BASE_URL", "http://127.0.0.1:8000")
TEST_PASSWORD = "F1shcake"
WAIT_TIMEOUT = 5


# ---------------------------------------------------------------------------
# Selenium helpers
# ---------------------------------------------------------------------------


def wait_for_clickable(driver, element_id, timeout=WAIT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.ID, element_id))
    )


def wait_for_text(driver, text, element_id, timeout=WAIT_TIMEOUT):
    WebDriverWait(driver, timeout).until(
        EC.text_to_be_present_in_element((By.ID, element_id), text)
    )


def selenium_login(driver, user):
    driver.get(f"{BASE_URL}/accounts/login")
    driver.find_element(By.ID, "id_username").send_keys(user.username)
    driver.find_element(By.ID, "id_password").send_keys(TEST_PASSWORD)
    driver.find_element(By.CLASS_NAME, "btn").click()


# ---------------------------------------------------------------------------
# Event entry helpers (pytest-compatible, no manager dependency)
# ---------------------------------------------------------------------------


def _enter_event(driver, entry_url, player_list, player0_payment_type=None):
    """Navigate to the entry page and fill in the form."""

    driver.get(BASE_URL + entry_url)

    if player0_payment_type:
        wait_for_clickable(driver, "id_player0_payment")
        Select(driver.find_element(By.ID, "id_player0_payment")).select_by_value(
            player0_payment_type
        )

    for player_no, player in enumerate(player_list, start=1):
        wait_for_clickable(driver, f"id_player{player_no}")
        Select(driver.find_element(By.ID, f"id_player{player_no}")).select_by_value(
            str(player[0].id)
        )
        wait_for_clickable(driver, f"id_player{player_no}_payment")
        Select(
            driver.find_element(By.ID, f"id_player{player_no}_payment")
        ).select_by_value(player[1])

    wait_for_clickable(driver, "id_checkout").click()


def _assert_entries_and_cleanup(event, player_list):
    """Assert payment statuses for all players, then delete the entry and emails."""

    last_eep = None
    for player in player_list:
        eep = EventEntryPlayer.objects.filter(
            event_entry__event=event, player=player[0]
        ).first()
        assert eep is not None, f"No EventEntryPlayer found for {player[0]}"
        assert eep.payment_status == player[2], (
            f"{player[0]}: expected payment_status='{player[2]}', "
            f"got '{eep.payment_status}'"
        )
        last_eep = eep

    last_eep.event_entry.delete()
    Email.objects.all().delete()


def _assert_balances(player_list, balances_before, event):
    """Assert each player's balance changed by the expected entry fee."""

    bridge_credit_types = ["my-system-dollars", "their-system-dollars"]

    for player in player_list:
        balance_before = balances_before[player[0]]
        balance_after = get_balance(player[0])

        # player[4] (when present and True) means a manual payment was made —
        # balance should be unchanged
        manual_payment = len(player) >= 5 and player[4]
        if manual_payment or player[1] not in bridge_credit_types:
            expected_deduction = 0
        else:
            expected_deduction = (
                0  # paid via Bridge Credits but by Keith, not the player
            )

        assert balance_after == balance_before - expected_deduction, (
            f"{player[0]}: balance before={balance_before}, after={balance_after}, "
            f"expected deduction={expected_deduction}"
        )


def enter_event_and_check(
    driver, event, entry_url, player_list, player0_payment_type=None
):
    """Enter an event via Selenium and assert payment status and balances."""

    balances_before = {p[0]: get_balance(p[0]) for p in player_list}
    _enter_event(driver, entry_url, player_list, player0_payment_type)
    wait_for_text(driver, "Congresses", "t_congress_heading")
    _assert_entries_and_cleanup(event, player_list)
    _assert_balances(player_list, balances_before, event)


def enter_event_then_pay_and_check(
    driver, event, entry_url, player_list, player0_payment_type=None
):
    """Enter an event, complete Stripe payment, then assert."""

    _enter_event(driver, entry_url, player_list, player0_payment_type)
    wait_for_text(driver, "Credit Card Payment", "id_credit_card_header")

    # Stripe manual payment steps (adapted from payments.tests.integration.common_functions)
    # Fill in test card details on the Stripe-hosted iframe
    wait_for_clickable(driver, "cardNumber")
    driver.find_element(By.ID, "cardNumber").send_keys("4242424242424242")
    driver.find_element(By.ID, "cardExpiry").send_keys("1230")
    driver.find_element(By.ID, "cardCvc").send_keys("123")
    driver.find_element(By.ID, "billingName").send_keys("Test User")
    driver.find_element(By.ID, "submitButton").click()

    sleep(5)
    _assert_entries_and_cleanup(event, player_list)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def driver():
    options = ChromeOptions()
    options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.notifications": 2,
            "autofill.credit_card_enabled": False,
        },
    )
    options.timeouts = {"implicit": 5000}
    d = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    yield d
    d.quit()


@pytest.fixture(scope="module")
def users(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return {
            "keith": User.objects.get(username="110"),
            "lucy": User.objects.get(username="111"),
            "morris": User.objects.get(username="112"),
            "natalie": User.objects.get(username="113"),
            "penelope": User.objects.get(username="115"),
        }


@pytest.fixture(scope="module")
def event_entry_setup(driver, users, django_db_setup, django_db_blocker):
    """Configure congress, create team mates, fund Keith, and log in via Selenium."""

    with django_db_blocker.unblock():
        keith = users["keith"]
        lucy = users["lucy"]
        morris = users["morris"]
        natalie = users["natalie"]
        penelope = users["penelope"]

        # Configure congress payment methods
        congress = Congress.objects.get(pk=1)
        congress.payment_method_bank_transfer = True
        congress.payment_method_cash = True
        congress.payment_method_cheques = True
        congress.payment_method_off_system_pp = True
        congress.bank_transfer_details = "Gold bars"
        congress.cheque_details = "Pay to cash"
        congress.save()

        pairs_event = Event.objects.get(pk=1)
        teams_event = Event.objects.get(pk=2)

        pairs_entry_url = reverse(
            "events:enter_event", kwargs={"congress_id": 1, "event_id": 1}
        )
        teams_entry_url = reverse(
            "events:enter_event", kwargs={"congress_id": 1, "event_id": 2}
        )

        # Set up team mates for Keith
        for user, team_mate in [
            (lucy, keith),
            (morris, keith),
            (natalie, keith),
            (penelope, keith),
            (keith, lucy),
            (keith, morris),
            (keith, natalie),
            (keith, penelope),
        ]:
            TeamMate.objects.get_or_create(
                user=user, team_mate=team_mate, defaults={"make_payments": True}
            )

        # Give Keith funds
        update_account(
            member=keith, amount=1000.0, description="Cash", payment_type="Refund"
        )

    selenium_login(driver, users["keith"])

    return {
        "driver": driver,
        "users": users,
        "congress": congress,
        "pairs_event": pairs_event,
        "teams_event": teams_event,
        "pairs_entry_url": pairs_entry_url,
        "teams_entry_url": teams_entry_url,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventEntry:
    """Tests for event entry through the UI (Selenium)."""

    def test_a1_pairs_both_bridge_credits(self, event_entry_setup):
        """Keith enters pairs event and pays for Lucy with Bridge Credits."""

        s = event_entry_setup
        enter_event_and_check(
            driver=s["driver"],
            event=s["pairs_event"],
            entry_url=s["pairs_entry_url"],
            player_list=[[s["users"]["lucy"], "my-system-dollars", "Paid"]],
        )

    def test_a1_pairs_bridge_credits_and_bank_transfer(self, event_entry_setup):
        """Keith pays Bridge Credits for himself; Lucy is set to Bank Transfer."""

        s = event_entry_setup
        enter_event_and_check(
            driver=s["driver"],
            event=s["pairs_event"],
            entry_url=s["pairs_entry_url"],
            player_list=[[s["users"]["lucy"], "bank-transfer", "Pending Manual"]],
        )

    def test_a1_pairs_cash_and_bank_transfer(self, event_entry_setup):
        """Keith pays cash for himself; Lucy is set to Bank Transfer."""

        s = event_entry_setup
        enter_event_and_check(
            driver=s["driver"],
            event=s["pairs_event"],
            entry_url=s["pairs_entry_url"],
            player_list=[[s["users"]["lucy"], "bank-transfer", "Pending Manual"]],
            player0_payment_type="cash",
        )

    def test_a1_pairs_insufficient_funds_stripe(self, event_entry_setup):
        """Keith has no Bridge Credits and completes payment via Stripe."""

        s = event_entry_setup
        keith = s["users"]["keith"]

        update_account(
            member=keith,
            amount=-get_balance(keith),
            description="Empty Keith out",
            payment_type="Refund",
        )

        enter_event_then_pay_and_check(
            driver=s["driver"],
            event=s["pairs_event"],
            entry_url=s["pairs_entry_url"],
            player_list=[[s["users"]["lucy"], "my-system-dollars", "Paid", True]],
        )

    def test_a2_teams_all_bridge_credits(self, event_entry_setup):
        """Keith enters teams event and pays for Lucy, Morris, and Natalie."""

        s = event_entry_setup

        update_account(
            member=s["users"]["keith"],
            amount=1000.0,
            description="Cash",
            payment_type="Refund",
        )

        enter_event_and_check(
            driver=s["driver"],
            event=s["teams_event"],
            entry_url=s["teams_entry_url"],
            player_list=[
                [s["users"]["lucy"], "my-system-dollars", "Paid"],
                [s["users"]["morris"], "my-system-dollars", "Paid"],
                [s["users"]["natalie"], "my-system-dollars", "Paid"],
            ],
        )

    def test_a3_cancel_entry_records_event_id(self, event_entry_setup):
        """Withdrawing from an event sets event_id on both transaction records (COB-822)."""

        s = event_entry_setup
        driver = s["driver"]

        event = Event.objects.last()
        driver.get(
            f"{BASE_URL}/events/congress/event/change-entry"
            f"/{event.congress.id}/{event.id}"
        )

        wait_for_clickable(driver, "t_withdraw").click()
        wait_for_clickable(driver, "t_confirm").click()
        sleep(1)

        last_tran = MemberTransaction.objects.last()
        last_org_tran = OrganisationTransaction.objects.last()

        assert (
            last_tran.event_id == event.id
        ), f"MemberTransaction.event_id={last_tran.event_id}, expected {event.id}"
        assert (
            last_org_tran.event_id == event.id
        ), f"OrganisationTransaction.event_id={last_org_tran.event_id}, expected {event.id}"
