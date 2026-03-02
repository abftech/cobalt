"""Unit tests for XeroApi methods in xero/core.py

Two module-level flags control how the tests run:

    MOCK_XERO_API (bool, default True)
        When True  — all Xero HTTP calls are replaced with unittest.mock
                     stubs.  Tests run offline with no credentials required.
        When False — tests make real HTTP requests to Xero.  Read the
                     "Live mode" section at the bottom of this file before
                     flipping this flag.

    LIVE_XERO_CONTACT_ID (str, default "")
        Only relevant when MOCK_XERO_API=False.  Set this to the UUID of a
        Contact that already exists in your Xero demo/sandbox company.
        Invoice and payment tests will be skipped if this is empty.
"""

from contextlib import nullcontext
from datetime import date
from unittest.mock import patch

from organisations.models import Organisation
from tests.test_manager import CobaltTestManagerUnit
from xero.core import XeroApi
from xero.models import XeroCredentials, XeroInvoice

# ---------------------------------------------------------------------------
# Flags — edit these to switch between mocked and live API calls
# ---------------------------------------------------------------------------

MOCK_XERO_API = True

# UUID of an existing Xero Contact in your sandbox/demo company.
# Only needed when MOCK_XERO_API = False.
LIVE_XERO_CONTACT_ID = ""


def _make_api() -> XeroApi:
    """Return a XeroApi instance, ensuring a credentials row exists."""
    XeroCredentials.objects.get_or_create()
    return XeroApi()


def _line_items() -> list:
    """Standard line items reused across invoice tests."""
    return [
        {
            "description": "Test charge",
            "quantity": 2,
            "unit_amount": 50.00,
            "account_code": "200",
        }
    ]


def _patch_post(xero, response):
    """Patch xero_api_post when mocking; no-op context otherwise."""
    if MOCK_XERO_API:
        return patch.object(xero, "xero_api_post", return_value=response)
    return nullcontext(None)


def _patch_get(xero, response):
    """Patch xero_api_get when mocking; no-op context otherwise."""
    if MOCK_XERO_API:
        return patch.object(xero, "xero_api_get", return_value=response)
    return nullcontext(None)


def _skip_in_live_mode(manager, test_name):
    """Record a skip and return True when running against the live Xero API.

    Use this at the top of any test that inspects mock call arguments, since
    those assertions cannot be made against real HTTP calls.
    """
    if not MOCK_XERO_API:
        manager.save_results(
            status=True,
            test_name=f"{test_name} [SKIPPED — live mode]",
            test_description="Payload inspection test — skipped when MOCK_XERO_API=False",
            output="Skipped: this test verifies what was sent to Xero and requires mocking",
        )
        return True
    return False


def _skip_no_contact_id(manager, test_name):
    """Record a skip and return True in live mode when no contact ID is configured."""
    if not MOCK_XERO_API and not LIVE_XERO_CONTACT_ID:
        manager.save_results(
            status=True,
            test_name=f"{test_name} [SKIPPED — no LIVE_XERO_CONTACT_ID]",
            test_description="Set LIVE_XERO_CONTACT_ID at the top of this file to run this test in live mode",
            output="Skipped",
        )
        return True
    return False


class XeroApiTests:
    """Unit tests for XeroApi in xero/core.py

    Covers contact management (create/update/archive), invoice management
    (create/get/void), payment recording, and the listing methods
    (get_invoices_for_organisation, get_payments_for_organisation).
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager

        # Ensure a credentials row exists so XeroApi.__init__ succeeds
        XeroCredentials.objects.get_or_create()

        # Organisation used for the majority of tests
        self.org = Organisation(
            org_id="T001",
            name="Test Bridge Club",
            secretary=self.manager.alan,
            type="Club",
            club_email="test@example.com",
            address1="123 Test Street",
            suburb="Testville",
            state="NSW",
            postcode="2000",
        )
        self.org.save()

        # Organisation that deliberately has no xero_contact_id
        self.org_no_contact = Organisation(
            org_id="T002",
            name="No Contact Club",
            secretary=self.manager.alan,
            type="Club",
        )
        self.org_no_contact.save()

        # In live mode use the pre-configured contact UUID; in mock mode use a
        # placeholder that the patched API will accept without complaint.
        self.contact_id = (
            LIVE_XERO_CONTACT_ID if not MOCK_XERO_API else "mock-contact-uuid"
        )

    # -----------------------------------------------------------------------
    # Contact: create
    # -----------------------------------------------------------------------

    def test_01_create_contact_success(self):
        """create_organisation_contact saves the returned ContactID on the org"""
        # Clear any residual contact_id so the method runs unconditionally
        self.org.xero_contact_id = ""
        self.org.save()

        mock_response = {"Contacts": [{"ContactID": "abc-123"}]}
        xero = _make_api()
        with _patch_post(xero, mock_response):
            result = xero.create_organisation_contact(self.org)

        self.org.refresh_from_db()
        if MOCK_XERO_API:
            status = result == "abc-123" and self.org.xero_contact_id == "abc-123"
            output = f"Returned: {result!r}. Saved on org: {self.org.xero_contact_id!r}"
        else:
            status = bool(result) and self.org.xero_contact_id == result
            output = f"Xero returned ContactID: {result!r}"

        self.manager.save_results(
            status=status,
            test_name="create_organisation_contact: success",
            test_description="Verify ContactID is returned and saved back to Organisation.xero_contact_id",
            output=output,
        )

    def test_02_create_contact_empty_response(self):
        """create_organisation_contact returns None when Xero returns no Contacts key"""
        if _skip_in_live_mode(
            self.manager, "create_organisation_contact: empty Xero response"
        ):
            return

        xero = _make_api()
        with patch.object(xero, "xero_api_post", return_value={}):
            result = xero.create_organisation_contact(self.org)

        self.manager.save_results(
            status=result is None,
            test_name="create_organisation_contact: empty Xero response",
            test_description="Verify None is returned when Xero returns no Contacts in the response",
            output=f"Got: {result!r}",
        )

    def test_03_create_contact_missing_contact_id_field(self):
        """create_organisation_contact returns None when response has no ContactID"""
        if _skip_in_live_mode(
            self.manager, "create_organisation_contact: missing ContactID"
        ):
            return

        xero = _make_api()
        with patch.object(
            xero, "xero_api_post", return_value={"Contacts": [{"Name": "X"}]}
        ):
            result = xero.create_organisation_contact(self.org)

        self.manager.save_results(
            status=result is None,
            test_name="create_organisation_contact: missing ContactID in response",
            test_description="Verify None is returned when the Contacts list item has no ContactID",
            output=f"Got: {result!r}",
        )

    # -----------------------------------------------------------------------
    # Contact: update
    # -----------------------------------------------------------------------

    def test_04_update_contact_success(self):
        """update_organisation_contact returns True when Xero acknowledges the update"""
        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_response = {"Contacts": [{"ContactID": self.contact_id}]}
        xero = _make_api()
        with _patch_post(xero, mock_response):
            result = xero.update_organisation_contact(self.org)

        self.manager.save_results(
            status=result is True,
            test_name="update_organisation_contact: success",
            test_description="Verify True is returned when Xero acknowledges the contact update",
            output=f"Returned: {result!r}",
        )

    def test_05_update_contact_no_xero_id(self):
        """update_organisation_contact returns False without calling Xero"""
        self.org_no_contact.xero_contact_id = ""
        self.org_no_contact.save()

        xero = _make_api()
        result = xero.update_organisation_contact(self.org_no_contact)

        self.manager.save_results(
            status=result is False,
            test_name="update_organisation_contact: no xero_contact_id",
            test_description="Verify False is returned immediately when the Organisation has no xero_contact_id",
            output=f"Returned: {result!r}",
        )

    # -----------------------------------------------------------------------
    # Contact: archive
    # -----------------------------------------------------------------------

    def test_06_archive_contact_success(self):
        """archive_organisation_contact clears xero_contact_id after archiving"""
        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_response = {
            "Contacts": [{"ContactID": self.contact_id, "ContactStatus": "ARCHIVED"}]
        }
        xero = _make_api()
        with _patch_post(xero, mock_response):
            result = xero.archive_organisation_contact(self.org)

        self.org.refresh_from_db()
        status = result is True and self.org.xero_contact_id == ""
        self.manager.save_results(
            status=status,
            test_name="archive_organisation_contact: success",
            test_description="Verify True is returned and xero_contact_id is cleared on the Organisation",
            output=f"Returned: {result!r}. xero_contact_id after: {self.org.xero_contact_id!r}",
        )

    def test_07_archive_contact_no_xero_id(self):
        """archive_organisation_contact returns False without calling Xero"""
        self.org_no_contact.xero_contact_id = ""
        self.org_no_contact.save()

        xero = _make_api()
        result = xero.archive_organisation_contact(self.org_no_contact)

        self.manager.save_results(
            status=result is False,
            test_name="archive_organisation_contact: no xero_contact_id",
            test_description="Verify False is returned immediately when org has no xero_contact_id",
            output=f"Returned: {result!r}",
        )

    # -----------------------------------------------------------------------
    # Invoice: create
    # -----------------------------------------------------------------------

    def test_08_create_invoice_accrec(self):
        """create_invoice creates an ACCREC invoice and saves a local XeroInvoice"""
        if _skip_no_contact_id(self.manager, "create_invoice: ACCREC"):
            return

        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_response = {
            "Invoices": [
                {
                    "InvoiceID": "inv-accrec",
                    "InvoiceNumber": "INV-0001",
                    "Status": "AUTHORISED",
                }
            ]
        }
        xero = _make_api()
        with _patch_post(xero, mock_response):
            invoice = xero.create_invoice(
                organisation=self.org,
                line_items=_line_items(),
                reference="Test ACCREC",
                invoice_type="ACCREC",
            )

        db_record = (
            XeroInvoice.objects.filter(organisation=self.org).order_by("-pk").first()
        )
        status = (
            invoice is not None
            and invoice.invoice_type == "ACCREC"
            and float(invoice.amount) == 100.00
            and db_record is not None
        )
        self.manager.save_results(
            status=status,
            test_name="create_invoice: ACCREC type",
            test_description="Verify an ACCREC invoice is created in Xero and a local XeroInvoice record is saved with the correct amount",
            output=f"invoice={invoice!r}. DB record: {db_record!r}",
        )

    def test_09_create_invoice_accpay(self):
        """create_invoice stores invoice_type=ACCPAY on the local record"""
        if _skip_no_contact_id(self.manager, "create_invoice: ACCPAY"):
            return

        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_response = {
            "Invoices": [
                {
                    "InvoiceID": "inv-accpay",
                    "InvoiceNumber": "BILL-0001",
                    "Status": "AUTHORISED",
                }
            ]
        }
        xero = _make_api()
        with _patch_post(xero, mock_response):
            invoice = xero.create_invoice(
                organisation=self.org,
                line_items=_line_items(),
                reference="Test ACCPAY",
                invoice_type="ACCPAY",
            )

        invoice_type = invoice.invoice_type if invoice else None
        self.manager.save_results(
            status=invoice is not None and invoice_type == "ACCPAY",
            test_name="create_invoice: ACCPAY type",
            test_description="Verify an ACCPAY (bill) invoice is stored with invoice_type=ACCPAY on the local record",
            output=f"invoice_type={invoice_type!r}",
        )

    def test_10_create_invoice_no_contact_id(self):
        """create_invoice returns None when org has no xero_contact_id"""
        xero = _make_api()
        result = xero.create_invoice(
            organisation=self.org_no_contact,
            line_items=_line_items(),
            reference="Should fail",
        )

        self.manager.save_results(
            status=result is None,
            test_name="create_invoice: no xero_contact_id returns None",
            test_description="Verify None is returned without calling Xero when the Organisation has no xero_contact_id",
            output=f"Returned: {result!r}",
        )

    def test_11_create_invoice_due_days(self):
        """create_invoice sets DueDate = Date + due_days in the Xero payload"""
        if _skip_in_live_mode(self.manager, "create_invoice: due_days in payload"):
            return

        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_response = {
            "Invoices": [
                {
                    "InvoiceID": "inv-due",
                    "InvoiceNumber": "INV-DUE",
                    "Status": "AUTHORISED",
                }
            ]
        }
        xero = _make_api()
        with patch.object(
            xero, "xero_api_post", return_value=mock_response
        ) as mock_post:
            xero.create_invoice(
                organisation=self.org,
                line_items=_line_items(),
                reference="Due days test",
                due_days=30,
            )

        inv = mock_post.call_args[0][1]["Invoices"][0]
        gap = (
            date.fromisoformat(inv["DueDate"]) - date.fromisoformat(inv["Date"])
        ).days
        self.manager.save_results(
            status=gap == 30,
            test_name="create_invoice: due_days respected in payload",
            test_description="Verify DueDate in the Xero payload is exactly due_days after Date",
            output=f"Date={inv['Date']!r}. DueDate={inv['DueDate']!r}. Gap={gap} days (expected 30)",
        )

    # -----------------------------------------------------------------------
    # Invoice: get / void
    # -----------------------------------------------------------------------

    def test_12_get_invoice_calls_correct_endpoint(self):
        """get_invoice hits /Invoices/{InvoiceID} and returns the raw response"""
        if _skip_in_live_mode(self.manager, "get_invoice: correct endpoint"):
            return

        xero = _make_api()
        mock_response = {"Invoices": [{"InvoiceID": "inv-123"}]}
        with patch.object(xero, "xero_api_get", return_value=mock_response) as mock_get:
            result = xero.get_invoice("inv-123")

        called_url = mock_get.call_args[0][0]
        self.manager.save_results(
            status=result == mock_response and "inv-123" in called_url,
            test_name="get_invoice: correct endpoint called",
            test_description="Verify get_invoice calls /Invoices/{InvoiceID} and returns the raw Xero response",
            output=f"URL called: {called_url!r}",
        )

    def test_13_void_invoice_updates_local_status(self):
        """void_invoice updates the local XeroInvoice status to VOIDED"""
        self.org.xero_contact_id = self.contact_id
        self.org.save()

        local_invoice = XeroInvoice(
            organisation=self.org,
            xero_invoice_id="inv-to-void",
            invoice_number="INV-9999",
            invoice_type="ACCREC",
            amount=100.00,
            status="AUTHORISED",
            reference="Void test",
            date=date.today(),
            due_date=date.today(),
        )
        local_invoice.save()

        mock_response = {"Invoices": [{"InvoiceID": "inv-to-void", "Status": "VOIDED"}]}
        xero = _make_api()
        with _patch_post(xero, mock_response):
            result = xero.void_invoice("inv-to-void")

        local_invoice.refresh_from_db()
        status = result is True and local_invoice.status == "VOIDED"
        self.manager.save_results(
            status=status,
            test_name="void_invoice: local status updated to VOIDED",
            test_description="Verify True is returned and the local XeroInvoice status becomes VOIDED",
            output=f"Returned: {result!r}. Local status: {local_invoice.status!r}",
        )

    def test_14_void_invoice_empty_response(self):
        """void_invoice returns False when Xero returns no Invoices"""
        if _skip_in_live_mode(self.manager, "void_invoice: empty response"):
            return

        xero = _make_api()
        with patch.object(xero, "xero_api_post", return_value={}):
            result = xero.void_invoice("inv-missing")

        self.manager.save_results(
            status=result is False,
            test_name="void_invoice: empty Xero response returns False",
            test_description="Verify False is returned when Xero returns no Invoices in the void response",
            output=f"Returned: {result!r}",
        )

    # -----------------------------------------------------------------------
    # Payment: create
    # -----------------------------------------------------------------------

    def test_15_create_payment_marks_invoice_paid(self):
        """create_payment updates the local XeroInvoice to PAID on success"""
        self.org.xero_contact_id = self.contact_id
        self.org.save()

        local_invoice = XeroInvoice(
            organisation=self.org,
            xero_invoice_id="inv-for-payment",
            invoice_number="INV-PAY-1",
            invoice_type="ACCREC",
            amount=200.00,
            status="AUTHORISED",
            reference="Payment test",
            date=date.today(),
            due_date=date.today(),
        )
        local_invoice.save()

        mock_response = {
            "Payments": [{"PaymentID": "pay-uuid", "Status": "AUTHORISED"}]
        }
        xero = _make_api()
        with _patch_post(xero, mock_response):
            xero.create_payment("inv-for-payment", 200.00)

        local_invoice.refresh_from_db()
        self.manager.save_results(
            status=local_invoice.status == "PAID",
            test_name="create_payment: local invoice marked as PAID",
            test_description="Verify the local XeroInvoice status is updated to PAID after a successful Xero payment response",
            output=f"Local invoice status: {local_invoice.status!r}",
        )

    def test_16_create_payment_uses_default_account_code(self):
        """create_payment sends XERO_BANK_ACCOUNT_CODE from settings by default"""
        if _skip_in_live_mode(self.manager, "create_payment: default account code"):
            return

        from cobalt.settings import XERO_BANK_ACCOUNT_CODE

        xero = _make_api()
        with patch.object(
            xero, "xero_api_post", return_value={"Payments": [{"Status": "AUTHORISED"}]}
        ) as mock_post:
            xero.create_payment("some-invoice-id", 50.00)

        account_code_sent = mock_post.call_args[0][1]["Payments"][0]["Account"]["Code"]
        self.manager.save_results(
            status=account_code_sent == XERO_BANK_ACCOUNT_CODE,
            test_name="create_payment: uses XERO_BANK_ACCOUNT_CODE by default",
            test_description="Verify the account code in the Xero payload matches XERO_BANK_ACCOUNT_CODE from settings when no account_code argument is provided",
            output=f"Sent: {account_code_sent!r}. Settings value: {XERO_BANK_ACCOUNT_CODE!r}",
        )

    def test_17_create_payment_custom_account_code(self):
        """create_payment uses the account_code argument when provided"""
        if _skip_in_live_mode(self.manager, "create_payment: custom account_code"):
            return

        xero = _make_api()
        with patch.object(
            xero, "xero_api_post", return_value={"Payments": [{"Status": "AUTHORISED"}]}
        ) as mock_post:
            xero.create_payment("some-invoice-id", 50.00, account_code="CUSTOM-99")

        account_code_sent = mock_post.call_args[0][1]["Payments"][0]["Account"]["Code"]
        self.manager.save_results(
            status=account_code_sent == "CUSTOM-99",
            test_name="create_payment: custom account_code overrides setting",
            test_description="Verify the account_code argument takes precedence over XERO_BANK_ACCOUNT_CODE from settings",
            output=f"Sent: {account_code_sent!r}. Expected: 'CUSTOM-99'",
        )

    def test_18_create_payment_defaults_to_today(self):
        """create_payment uses today's date when payment_date is not provided"""
        if _skip_in_live_mode(self.manager, "create_payment: default date"):
            return

        xero = _make_api()
        with patch.object(
            xero, "xero_api_post", return_value={"Payments": [{"Status": "AUTHORISED"}]}
        ) as mock_post:
            xero.create_payment("some-invoice-id", 50.00)

        date_sent = mock_post.call_args[0][1]["Payments"][0]["Date"]
        expected = f"{date.today():%Y-%m-%d}"
        self.manager.save_results(
            status=date_sent == expected,
            test_name="create_payment: defaults to today's date",
            test_description="Verify the Date in the Xero payload is today when no payment_date argument is provided",
            output=f"Sent: {date_sent!r}. Expected: {expected!r}",
        )

    # -----------------------------------------------------------------------
    # Listing: get_invoices_for_organisation
    # -----------------------------------------------------------------------

    def test_19_list_invoices_no_date_range(self):
        """get_invoices_for_organisation returns all invoices; no date params in URL"""
        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_invoices = [{"InvoiceID": "a"}, {"InvoiceID": "b"}]
        xero = _make_api()
        with _patch_get(xero, {"Invoices": mock_invoices}) as mock_get:
            result = xero.get_invoices_for_organisation(self.org)

        if MOCK_XERO_API:
            called_url = mock_get.call_args[0][0]
            status = (
                result == mock_invoices
                and "DateFrom" not in called_url
                and "DateTo" not in called_url
            )
            output = f"URL: {called_url!r}. Count: {len(result)}"
        else:
            status = isinstance(result, list)
            output = f"Returned {len(result)} invoices from Xero"

        self.manager.save_results(
            status=status,
            test_name="get_invoices_for_organisation: no date range",
            test_description="Verify invoices are returned and no date params appear when none are specified",
            output=output,
        )

    def test_20_list_invoices_with_date_range(self):
        """get_invoices_for_organisation adds DateFrom and DateTo to the request URL"""
        if _skip_in_live_mode(
            self.manager, "get_invoices_for_organisation: date range in URL"
        ):
            return

        self.org.xero_contact_id = self.contact_id
        self.org.save()

        xero = _make_api()
        with patch.object(
            xero, "xero_api_get", return_value={"Invoices": []}
        ) as mock_get:
            xero.get_invoices_for_organisation(
                self.org,
                date_from=date(2026, 1, 1),
                date_to=date(2026, 3, 31),
            )

        called_url = mock_get.call_args[0][0]
        self.manager.save_results(
            status="DateFrom=2026-01-01" in called_url
            and "DateTo=2026-03-31" in called_url,
            test_name="get_invoices_for_organisation: date range in URL",
            test_description="Verify DateFrom and DateTo appear in the Xero API request URL",
            output=f"URL: {called_url!r}",
        )

    def test_21_list_invoices_no_contact_id(self):
        """get_invoices_for_organisation returns [] without calling Xero"""
        xero = _make_api()
        with patch.object(xero, "xero_api_get") as mock_get:
            result = xero.get_invoices_for_organisation(self.org_no_contact)

        self.manager.save_results(
            status=result == [] and not mock_get.called,
            test_name="get_invoices_for_organisation: no xero_contact_id returns []",
            test_description="Verify an empty list is returned and Xero is not called when the org has no xero_contact_id",
            output=f"Returned: {result!r}. Xero called: {mock_get.called}",
        )

    # -----------------------------------------------------------------------
    # Listing: get_payments_for_organisation
    # -----------------------------------------------------------------------

    def test_22_list_payments_extracts_from_paid_invoices(self):
        """get_payments_for_organisation flattens payments from all returned invoices"""
        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_invoices = [
            {
                "InvoiceID": "inv-a",
                "InvoiceNumber": "INV-0010",
                "Reference": "Ref-A",
                "Payments": [
                    {"PaymentID": "pay-1", "Amount": 100.0},
                    {"PaymentID": "pay-2", "Amount": 50.0},
                ],
            },
            {
                "InvoiceID": "inv-b",
                "InvoiceNumber": "INV-0011",
                "Reference": "Ref-B",
                "Payments": [{"PaymentID": "pay-3", "Amount": 200.0}],
            },
        ]
        xero = _make_api()
        with _patch_get(xero, {"Invoices": mock_invoices}):
            result = xero.get_payments_for_organisation(self.org)

        if MOCK_XERO_API:
            pay_ids = [p["PaymentID"] for p in result]
            status = len(result) == 3 and pay_ids == ["pay-1", "pay-2", "pay-3"]
            output = f"Count: {len(result)} (expected 3). PaymentIDs: {pay_ids}"
        else:
            status = isinstance(result, list)
            output = f"Returned {len(result)} payments from Xero"

        self.manager.save_results(
            status=status,
            test_name="get_payments_for_organisation: payments extracted from all invoices",
            test_description="Verify all payment dicts from all paid invoices are returned as a flat list",
            output=output,
        )

    def test_23_list_payments_invoice_context_attached(self):
        """get_payments_for_organisation attaches InvoiceID, InvoiceNumber, InvoiceReference"""
        if _skip_in_live_mode(
            self.manager, "get_payments_for_organisation: invoice context"
        ):
            return

        self.org.xero_contact_id = self.contact_id
        self.org.save()

        mock_invoices = [
            {
                "InvoiceID": "inv-ctx",
                "InvoiceNumber": "INV-CTX",
                "Reference": "Context Test",
                "Payments": [{"PaymentID": "pay-ctx", "Amount": 75.0}],
            }
        ]
        xero = _make_api()
        with patch.object(
            xero, "xero_api_get", return_value={"Invoices": mock_invoices}
        ):
            result = xero.get_payments_for_organisation(self.org)

        payment = result[0]
        status = (
            payment.get("InvoiceID") == "inv-ctx"
            and payment.get("InvoiceNumber") == "INV-CTX"
            and payment.get("InvoiceReference") == "Context Test"
            and payment.get("PaymentID") == "pay-ctx"
        )
        self.manager.save_results(
            status=status,
            test_name="get_payments_for_organisation: invoice context on each payment",
            test_description="Verify InvoiceID, InvoiceNumber, and InvoiceReference are attached to each payment dict",
            output=f"InvoiceID={payment.get('InvoiceID')!r} InvoiceNumber={payment.get('InvoiceNumber')!r} InvoiceReference={payment.get('InvoiceReference')!r}",
        )

    def test_24_list_payments_with_date_range(self):
        """get_payments_for_organisation includes DateFrom, DateTo and Statuses=PAID in URL"""
        if _skip_in_live_mode(
            self.manager, "get_payments_for_organisation: date range in URL"
        ):
            return

        self.org.xero_contact_id = self.contact_id
        self.org.save()

        xero = _make_api()
        with patch.object(
            xero, "xero_api_get", return_value={"Invoices": []}
        ) as mock_get:
            xero.get_payments_for_organisation(
                self.org,
                date_from=date(2026, 6, 1),
                date_to=date(2026, 6, 30),
            )

        called_url = mock_get.call_args[0][0]
        status = (
            "DateFrom=2026-06-01" in called_url
            and "DateTo=2026-06-30" in called_url
            and "Statuses=PAID" in called_url
        )
        self.manager.save_results(
            status=status,
            test_name="get_payments_for_organisation: date range and Statuses=PAID in URL",
            test_description="Verify DateFrom, DateTo, and Statuses=PAID are all present in the Xero API request URL",
            output=f"URL: {called_url!r}",
        )

    def test_25_list_payments_no_contact_id(self):
        """get_payments_for_organisation returns [] without calling Xero"""
        xero = _make_api()
        with patch.object(xero, "xero_api_get") as mock_get:
            result = xero.get_payments_for_organisation(self.org_no_contact)

        self.manager.save_results(
            status=result == [] and not mock_get.called,
            test_name="get_payments_for_organisation: no xero_contact_id returns []",
            test_description="Verify an empty list is returned and Xero is not called when org has no xero_contact_id",
            output=f"Returned: {result!r}. Xero called: {mock_get.called}",
        )


# =============================================================================
# Notes on running these tests in live mode (MOCK_XERO_API = False)
# =============================================================================
#
# BEFORE enabling live mode, read all of the following carefully.
#
# 1. USE A DEMO / SANDBOX COMPANY
#    Xero provides free "demo company" accounts.  Never run live tests
#    against a real company's Xero organisation — the tests create contacts,
#    invoices, and payments that will pollute real accounting data.
#
# 2. DATA IS NOT ROLLED BACK
#    Django's unit test framework rolls back database changes after each test
#    run, but Xero API calls are fire-and-forget HTTP requests.  Any contacts,
#    invoices, or payments created during a live test run will remain in Xero
#    permanently unless you delete them manually through the Xero UI or API.
#    Running the tests multiple times will create duplicate contacts and
#    multiple invoices for the same reference.
#
# 3. CREDENTIALS MUST BE VALID
#    `XeroApi.__init__` loads tokens from the `XeroCredentials` database row.
#    Before running live tests, complete the OAuth flow at /xero/initialise to
#    obtain a valid access token and refresh token.  The `refresh_xero_tokens`
#    method will auto-refresh an expired access token, but it cannot recover
#    from a missing or revoked refresh token — in that case you must re-run
#    the OAuth flow.
#
# 4. RATE LIMITS
#    Xero's standard API tier allows 60 calls per minute per app.  Running
#    all 25 tests in live mode will consume roughly 10–15 API calls, well
#    within the limit for a single run.  If you are also running other
#    Xero-connected processes, monitor your rate-limit usage.
#
# 5. CONTACT ID FOR INVOICE / PAYMENT TESTS
#    Tests 08–09 (create invoice) and 15 (create payment) need a valid Xero
#    Contact UUID.  Set LIVE_XERO_CONTACT_ID at the top of this file to the
#    UUID of a contact that exists in your demo company.  You can find it in
#    Xero's UI under Contacts, or by running the "list contacts" command from
#    the /xero/ admin page and copying a ContactID from the JSON output.
#    If LIVE_XERO_CONTACT_ID is empty, those tests are automatically skipped.
#
# 6. TESTS THAT ARE ALWAYS MOCKED
#    Tests 02, 03, 11, 12, 14, 16, 17, 18, 20, 23, 24 verify what was *sent*
#    to Xero (payload structure, URL parameters).  These assertions require
#    access to mock call arguments and cannot be made against live HTTP
#    responses.  They are automatically skipped when MOCK_XERO_API=False and
#    reported as passed with a "[SKIPPED]" suffix.
#
# QUICK START FOR LIVE TESTING
#   1. Point the app at a Xero demo company (set XERO_TENANT_NAME in settings).
#   2. Complete the OAuth flow: python manage.py runserver, visit /xero/initialise.
#   3. In Xero, create a contact and copy its UUID.
#   4. Set MOCK_XERO_API = False and LIVE_XERO_CONTACT_ID = "<uuid>" here.
#   5. Run: python manage.py run_tests_unit --app xero
