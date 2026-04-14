from unittest.mock import MagicMock, patch

from django.urls import reverse

from payments.views.core import update_account
from tests.test_manager import CobaltTestManagerUnit


class PaymentsViewsTests:
    """Unit tests for player-facing payment views in payments/views/players.py

    Covers: statement, statement_csv, setup_autotopup, member_transfer,
    manual_topup, cancel_auto_top_up, and login-required redirects.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.alan = manager.alan
        # Give Alan a non-zero balance so the statement has real data
        update_account(
            member=self.alan,
            amount=100.0,
            description="Test setup credit",
            payment_type="Refund",
        )
        self.manager.login_test_client(self.alan)

    # ------------------------------------------------------------------ #
    # statement                                                            #
    # ------------------------------------------------------------------ #

    def test_01_statement_get(self):
        """GET /payments/ returns HTTP 200 for authenticated user."""
        url = reverse("payments:payments")
        response = self.manager.client.get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="statement GET",
            test_description="GET /payments/ for an authenticated user should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    def test_02_statement_requires_login(self):
        """GET /payments/ redirects unauthenticated users to login."""
        self.manager.client.logout()
        url = reverse("payments:payments")
        response = self.manager.client.get(url)
        # Re-login for subsequent tests
        self.manager.login_test_client(self.alan)
        self.manager.save_results(
            status=response.status_code in (301, 302),
            test_name="statement requires login",
            test_description="GET /payments/ without authentication should redirect to login",
            output=f"HTTP {response.status_code} (expected 302)",
        )

    # ------------------------------------------------------------------ #
    # statement_csv                                                        #
    # ------------------------------------------------------------------ #

    def test_03_statement_csv_get(self):
        """GET /payments/statement-csv/ returns HTTP 200 with CSV content-type."""
        url = reverse("payments:statement_csv")
        response = self.manager.client.get(url)
        is_csv = "text/csv" in response.get("Content-Type", "")
        self.manager.save_results(
            status=response.status_code == 200 and is_csv,
            test_name="statement_csv GET",
            test_description="GET /payments/statement-csv/ should return HTTP 200 with Content-Type text/csv",
            output=f"HTTP {response.status_code}, Content-Type={response.get('Content-Type', '')}",
        )

    # ------------------------------------------------------------------ #
    # member_transfer                                                      #
    # ------------------------------------------------------------------ #

    def test_04_member_transfer_get(self):
        """GET /payments/member-transfer/ returns HTTP 200."""
        url = reverse("payments:member_transfer")
        response = self.manager.client.get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="member_transfer GET",
            test_description="GET /payments/member-transfer/ for an authenticated user should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # manual_topup                                                         #
    # ------------------------------------------------------------------ #

    def test_05_manual_topup_get(self):
        """GET /payments/manual-topup/ returns HTTP 200."""
        url = reverse("payments:manual_topup")
        response = self.manager.client.get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="manual_topup GET",
            test_description="GET /payments/manual-topup/ for an authenticated user should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # setup_autotopup                                                      #
    # ------------------------------------------------------------------ #

    def test_06_setup_autotopup_get(self):
        """GET /payments/setup-autotopup/ returns HTTP 200.

        Alan does not have stripe_auto_confirmed='On', so the view calls
        stripe_create_customer which calls stripe.Customer.create — mock it.
        """
        url = reverse("payments:setup_autotopup")
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock_test"
        with patch(
            "payments.views.players.stripe.Customer.create", return_value=mock_customer
        ):
            response = self.manager.client.get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="setup_autotopup GET",
            test_description="GET /payments/setup-autotopup/ should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # cancel_auto_top_up                                                   #
    # ------------------------------------------------------------------ #

    def test_07_cancel_auto_top_up_post(self):
        """POST /payments/cancel-autotopup/ disables auto top up and redirects."""
        from accounts.models import User

        # Set up Alan as if he had auto top up enabled
        self.alan.stripe_auto_confirmed = "On"
        self.alan.auto_amount = 50.0
        self.alan.stripe_customer_id = "cus_test_cancel"
        self.alan.save()

        url = reverse("payments:cancel_autotopup")
        response = self.manager.client.post(url, {"stop_auto": "1"})

        # Reload from DB to check DB state and restore in-memory object
        refreshed = User.objects.get(pk=self.alan.pk)
        # Reset in-memory object so subsequent test classes start clean
        self.alan.stripe_auto_confirmed = refreshed.stripe_auto_confirmed
        self.alan.auto_amount = refreshed.auto_amount
        self.alan.stripe_customer_id = refreshed.stripe_customer_id

        self.manager.save_results(
            status=response.status_code in (301, 302)
            and refreshed.stripe_auto_confirmed == "Off",
            test_name="cancel_auto_top_up POST",
            test_description="POST to cancel-autotopup should redirect and set stripe_auto_confirmed='Off' in the DB",
            output=f"HTTP {response.status_code}, stripe_auto_confirmed={refreshed.stripe_auto_confirmed!r}",
        )
