from unittest.mock import MagicMock, patch

from payments.models import MemberTransaction, StripeTransaction
from payments.views.core import (
    _auto_topup_member_handle_failure,
    auto_topup_member,
    callback_router,
    get_balance,
    get_balance_detail,
    low_balance_warning,
    member_to_member_transfer_callback,
    stripe_webhook_manual,
    update_account,
)
from tests.test_manager import CobaltTestManagerUnit


class PaymentsCoreTests:
    """Unit tests for payments/views/core.py

    Covers: get_balance, get_balance_detail, update_account, auto_topup_member
    (guard conditions and mocked success/failure paths), low_balance_warning,
    stripe_webhook_manual, callback_router, and member_to_member_transfer_callback.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.alan = manager.alan
        self.betty = manager.betty

    # ------------------------------------------------------------------ #
    # get_balance                                                          #
    # ------------------------------------------------------------------ #

    def test_01_get_balance_no_transactions(self):
        """get_balance returns 0.0 when member has no transactions."""
        # Gary (106) has no transactions in either test database
        balance = get_balance(self.manager.gary)
        self.manager.save_results(
            status=balance == 0.0,
            test_name="get_balance — no transactions",
            test_description="get_balance returns 0.0 when the member has no MemberTransaction rows",
            output=f"Got {balance!r}, expected 0.0",
        )

    def test_02_get_balance_after_update(self):
        """get_balance reflects a credited transaction."""
        update_account(
            member=self.alan,
            amount=50.0,
            description="Test credit",
            payment_type="Refund",
        )
        balance = get_balance(self.alan)
        self.manager.save_results(
            status=balance >= 50.0,
            test_name="get_balance — after credit",
            test_description="get_balance returns at least the amount credited via update_account",
            output=f"Balance after 50.0 credit: {balance!r}",
        )

    # ------------------------------------------------------------------ #
    # get_balance_detail                                                   #
    # ------------------------------------------------------------------ #

    def test_03_get_balance_detail_no_transactions(self):
        """get_balance_detail returns zero dict when member has no transactions."""
        # Heidi (107) has no transactions in either test database
        detail = get_balance_detail(self.manager.heidi)
        self.manager.save_results(
            status=detail["balance"] == "0" and detail["balance_num"] is None,
            test_name="get_balance_detail — no transactions",
            test_description="get_balance_detail returns {'balance': '0', 'balance_num': None} for a member with no transactions",
            output=f"Got {detail!r}",
        )

    def test_04_get_balance_detail_after_update(self):
        """get_balance_detail has numeric balance after a transaction."""
        update_account(
            member=self.betty,
            amount=25.0,
            description="Test credit for detail",
            payment_type="Refund",
        )
        detail = get_balance_detail(self.betty)
        self.manager.save_results(
            status=detail["balance_num"] is not None
            and float(detail["balance_num"]) >= 25.0,
            test_name="get_balance_detail — after credit",
            test_description="get_balance_detail returns a non-None balance_num after a transaction is created",
            output=f"Got {detail!r}",
        )

    # ------------------------------------------------------------------ #
    # update_account                                                       #
    # ------------------------------------------------------------------ #

    def test_05_update_account_creates_transaction(self):
        """update_account creates a MemberTransaction row."""
        before = MemberTransaction.objects.filter(member=self.alan).count()
        update_account(
            member=self.alan,
            amount=10.0,
            description="Test transaction",
            payment_type="Refund",
        )
        after = MemberTransaction.objects.filter(member=self.alan).count()
        self.manager.save_results(
            status=after == before + 1,
            test_name="update_account — creates MemberTransaction",
            test_description="update_account should insert exactly one new MemberTransaction row",
            output=f"Before: {before}, After: {after}",
        )

    def test_06_update_account_balance_increases(self):
        """update_account correctly adds amount to running balance."""
        balance_before = get_balance(self.alan)
        update_account(
            member=self.alan,
            amount=20.0,
            description="Balance increase test",
            payment_type="Refund",
        )
        balance_after = get_balance(self.alan)
        self.manager.save_results(
            status=abs((balance_after - balance_before) - 20.0) < 0.01,
            test_name="update_account — balance increases by amount",
            test_description="After crediting 20.0 the balance should increase by exactly 20.0",
            output=f"Before: {balance_before}, After: {balance_after}, diff: {balance_after - balance_before}",
        )

    def test_07_update_account_debit_decreases_balance(self):
        """update_account with negative amount decreases the balance."""
        # First credit enough to go positive
        update_account(
            member=self.alan,
            amount=100.0,
            description="Setup credit",
            payment_type="Refund",
        )
        balance_before = get_balance(self.alan)
        update_account(
            member=self.alan,
            amount=-30.0,
            description="Debit test",
            payment_type="Club Payment",
        )
        balance_after = get_balance(self.alan)
        self.manager.save_results(
            status=abs((balance_before - balance_after) - 30.0) < 0.01,
            test_name="update_account — debit decreases balance",
            test_description="Passing a negative amount to update_account should reduce the balance by that amount",
            output=f"Before: {balance_before}, After: {balance_after}",
        )

    def test_08_update_account_returns_transaction(self):
        """update_account returns the created MemberTransaction."""
        tran = update_account(
            member=self.alan,
            amount=5.0,
            description="Return value test",
            payment_type="Refund",
        )
        self.manager.save_results(
            status=isinstance(tran, MemberTransaction) and tran.pk is not None,
            test_name="update_account — returns MemberTransaction",
            test_description="update_account should return the new MemberTransaction object with a valid pk",
            output=f"Returned {type(tran).__name__}, pk={getattr(tran, 'pk', None)}",
        )

    # ------------------------------------------------------------------ #
    # auto_topup_member — guard conditions                                 #
    # ------------------------------------------------------------------ #

    def test_09_auto_topup_not_configured(self):
        """auto_topup_member returns False when stripe_auto_confirmed != 'On'."""
        # Test users don't have auto top up configured
        success, message = auto_topup_member(self.alan)
        self.manager.save_results(
            status=not success and "not set up" in message.lower(),
            test_name="auto_topup_member — not configured",
            test_description="auto_topup_member returns (False, ...) when stripe_auto_confirmed is not 'On'",
            output=f"success={success!r}, message={message!r}",
        )

    def test_10_auto_topup_no_customer_id(self):
        """auto_topup_member returns False when stripe_customer_id is missing."""
        self.alan.stripe_auto_confirmed = "On"
        self.alan.stripe_customer_id = ""
        success, message = auto_topup_member(self.alan)
        # Reset user state
        self.alan.stripe_auto_confirmed = "Off"
        self.alan.stripe_customer_id = None
        self.manager.save_results(
            status=not success and "customer id" in message.lower(),
            test_name="auto_topup_member — no customer id",
            test_description="auto_topup_member returns (False, ...) when stripe_auto_confirmed='On' but stripe_customer_id is empty",
            output=f"success={success!r}, message={message!r}",
        )

    # ------------------------------------------------------------------ #
    # auto_topup_member — mocked success path                              #
    # ------------------------------------------------------------------ #

    def test_11_auto_topup_success(self):
        """auto_topup_member succeeds when Stripe APIs return valid data."""
        self.alan.stripe_auto_confirmed = "On"
        self.alan.stripe_customer_id = "cus_test123"
        self.alan.auto_amount = 50.0

        mock_pay_method = MagicMock()
        mock_pay_method.id = "pm_test123"

        mock_pay_list = MagicMock()
        mock_pay_list.data = [mock_pay_method]

        mock_card = MagicMock()
        mock_card.brand = "visa"
        mock_card.country = "AU"
        mock_card.exp_month = 12
        mock_card.exp_year = 2028
        mock_card.last4 = "4242"

        mock_payload = MagicMock()
        mock_payload.id = "ch_test123"
        mock_payload.payment_method = "pm_test123"
        mock_payload.currency = "aud"
        mock_payload.receipt_url = "https://pay.stripe.com/receipts/test"
        mock_payload.payment_method_details.card = mock_card
        mock_payload.balance_transaction = "txn_test123"

        mock_intent = MagicMock()
        mock_intent.__contains__ = lambda self, key: key == "charges"
        mock_intent.charges.data = [mock_payload]

        with patch(
            "payments.views.core.stripe.PaymentMethod.list", return_value=mock_pay_list
        ):
            with patch(
                "payments.views.core.stripe.PaymentIntent.create",
                return_value=mock_intent,
            ):
                with patch("payments.views.core.contact_member"):
                    success, message = auto_topup_member(self.alan)

        # Reset user state
        self.alan.stripe_auto_confirmed = "Off"
        self.alan.stripe_customer_id = None

        self.manager.save_results(
            status=success is True,
            test_name="auto_topup_member — success path",
            test_description="auto_topup_member returns (True, ...) when Stripe APIs succeed",
            output=f"success={success!r}, message={message!r}",
        )

    # ------------------------------------------------------------------ #
    # _auto_topup_member_handle_failure                                    #
    # ------------------------------------------------------------------ #

    def test_12_auto_topup_handle_failure_disables_autotopup(self):
        """_auto_topup_member_handle_failure sets stripe_auto_confirmed to 'No'."""
        self.alan.stripe_auto_confirmed = "On"
        self.alan.save()

        mock_error = MagicMock()
        mock_error.error.message = "Your card was declined."

        with patch("payments.views.core.contact_member"):
            success, message = _auto_topup_member_handle_failure(
                mock_error, self.alan, 50.0
            )

        # Reload from DB to confirm the save() was called
        from accounts.models import User

        refreshed = User.objects.get(pk=self.alan.pk)

        self.manager.save_results(
            status=not success and refreshed.stripe_auto_confirmed == "No",
            test_name="_auto_topup_member_handle_failure — disables auto top up",
            test_description="After a failure, stripe_auto_confirmed should be set to 'No' in the DB",
            output=f"success={success!r}, stripe_auto_confirmed={refreshed.stripe_auto_confirmed!r}",
        )

        # Reset
        self.alan.stripe_auto_confirmed = "Off"
        self.alan.save()

    def test_13_auto_topup_handle_failure_returns_false(self):
        """_auto_topup_member_handle_failure returns (False, message)."""
        mock_error = MagicMock()
        mock_error.error.message = "Insufficient funds."

        with patch("payments.views.core.contact_member"):
            success, message = _auto_topup_member_handle_failure(
                mock_error, self.alan, 25.0
            )

        self.manager.save_results(
            status=not success and "Insufficient funds" in message,
            test_name="_auto_topup_member_handle_failure — returns False",
            test_description="_auto_topup_member_handle_failure returns (False, message) containing the error text",
            output=f"success={success!r}, message={message!r}",
        )

    # ------------------------------------------------------------------ #
    # low_balance_warning                                                  #
    # ------------------------------------------------------------------ #

    def test_14_low_balance_warning_sends_email(self):
        """low_balance_warning sends an email when receive_low_balance_emails is True."""
        self.alan.receive_low_balance_emails = True

        with patch("payments.views.core.send_cobalt_email_with_template") as mock_send:
            low_balance_warning(self.alan)

        self.manager.save_results(
            status=mock_send.called,
            test_name="low_balance_warning — sends email",
            test_description="low_balance_warning should call send_cobalt_email_with_template when receive_low_balance_emails=True",
            output=f"send_cobalt_email_with_template called: {mock_send.called}",
        )

    def test_15_low_balance_warning_no_email_when_disabled(self):
        """low_balance_warning does not send email when receive_low_balance_emails is False."""
        self.alan.receive_low_balance_emails = False

        with patch("payments.views.core.send_cobalt_email_with_template") as mock_send:
            low_balance_warning(self.alan)

        self.manager.save_results(
            status=not mock_send.called,
            test_name="low_balance_warning — no email when disabled",
            test_description="low_balance_warning should NOT call send_cobalt_email_with_template when receive_low_balance_emails=False",
            output=f"send_cobalt_email_with_template called: {mock_send.called}",
        )

    # ------------------------------------------------------------------ #
    # stripe_webhook_manual                                                #
    # ------------------------------------------------------------------ #

    def test_16_stripe_webhook_manual_success(self):
        """stripe_webhook_manual updates StripeTransaction status to Succeeded."""
        # Create a StripeTransaction to update
        stripe_tran = StripeTransaction.objects.create(
            member=self.alan,
            description="Test manual payment",
            amount=75.0,
            status="Pending",
        )

        # Build a mock event matching the shape the function expects
        charge = MagicMock()
        charge.metadata.cobalt_pay_id = stripe_tran.pk
        charge.id = "ch_external_123"
        charge.payment_method = "pm_unique_abc"
        charge.currency = "aud"
        charge.receipt_url = "https://pay.stripe.com/receipts/test"
        charge.payment_method_details.card.brand = "visa"
        charge.payment_method_details.card.country = "AU"
        charge.payment_method_details.card.exp_month = 12
        charge.payment_method_details.card.exp_year = 2028
        charge.payment_method_details.card.last4 = "4242"
        charge.balance_transaction = "txn_abc"

        event = MagicMock()
        event.data.object = charge

        response = stripe_webhook_manual(event)

        stripe_tran.refresh_from_db()
        self.manager.save_results(
            status=stripe_tran.status == "Succeeded" and response.status_code == 200,
            test_name="stripe_webhook_manual — success",
            test_description="stripe_webhook_manual should set StripeTransaction.status='Succeeded' and return HTTP 200",
            output=f"status={stripe_tran.status!r}, HTTP {response.status_code}",
        )

    def test_17_stripe_webhook_manual_not_found(self):
        """stripe_webhook_manual returns 200 when StripeTransaction pk not found."""
        charge = MagicMock()
        charge.metadata.cobalt_pay_id = 999999  # non-existent pk
        charge.id = "ch_not_found"
        charge.payment_method = "pm_not_found"

        event = MagicMock()
        event.data.object = charge

        response = stripe_webhook_manual(event)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="stripe_webhook_manual — transaction not found",
            test_description="stripe_webhook_manual should return HTTP 200 even when the StripeTransaction pk is not found",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # callback_router                                                      #
    # ------------------------------------------------------------------ #

    def test_18_callback_router_no_route_code(self):
        """callback_router returns immediately when route_code is None."""
        # Should not raise — just returns None
        result = callback_router(None, None)
        self.manager.save_results(
            status=result is None,
            test_name="callback_router — None route_code",
            test_description="callback_router should return None immediately when route_code is None",
            output=f"Returned {result!r}",
        )

    def test_19_callback_router_unknown_route_code(self):
        """callback_router logs an error for an unknown route_code but does not raise."""
        with patch("payments.views.core.log_event") as mock_log:
            callback_router("UNKNOWN_CODE", "some_payload")

        self.manager.save_results(
            status=mock_log.called,
            test_name="callback_router — unknown route_code",
            test_description="callback_router should call log_event with severity CRITICAL for an unrecognised route_code",
            output=f"log_event called: {mock_log.called}, call args: {mock_log.call_args}",
        )

    # ------------------------------------------------------------------ #
    # member_to_member_transfer_callback                                   #
    # ------------------------------------------------------------------ #

    def test_20_m2m_callback_no_stripe_transaction(self):
        """member_to_member_transfer_callback returns None when stripe_transaction is None."""
        result = member_to_member_transfer_callback(None)
        self.manager.save_results(
            status=result is None,
            test_name="member_to_member_transfer_callback — no stripe transaction",
            test_description="member_to_member_transfer_callback returns None immediately when called with stripe_transaction=None",
            output=f"Returned {result!r}",
        )
