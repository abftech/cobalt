"""Unit tests for XeroApi.create_settlement_invoice() in xero/core.py.

Two module-level flags control how the tests run:

    MOCK_XERO_API (bool, default True)
        When True  — all Xero HTTP calls are replaced with unittest.mock stubs.
                     Tests run offline with no credentials required.
        When False — tests make real HTTP requests to Xero.  Read the live-mode
                     notes at the bottom of this file before flipping this flag.

    LIVE_XERO_CONTACT_ID (str, default "")
        Only relevant when MOCK_XERO_API=False.  Set this to the UUID of a
        Contact that already exists in your Xero demo/sandbox company.
"""

import re
from contextlib import nullcontext
from datetime import date
from unittest.mock import patch

from cobalt.settings import XERO_PAYABLE_ACCOUNT_CODE
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


def _patch_post(xero, response):
    """Patch xero_api_post when mocking; no-op context otherwise."""
    if MOCK_XERO_API:
        return patch.object(xero, "xero_api_post", return_value=response)
    return nullcontext(None)


def _skip_in_live_mode(manager, test_name):
    """Record a skip and return True when running against the live Xero API."""
    if not MOCK_XERO_API:
        manager.save_results(
            status=True,
            test_name=f"{test_name} [SKIPPED — live mode]",
            test_description="Payload inspection test — skipped when MOCK_XERO_API=False",
            output="Skipped: this test verifies what was sent to Xero and requires mocking",
        )
        return True
    return False


class CreateSettlementInvoiceTests:
    """Unit tests for XeroApi.create_settlement_invoice() in xero/core.py.

    Covers: PENDING_UPLOAD record creation, payload structure, cobalt_reference
    format, on-demand contact creation, failure handling, and field values.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager

        XeroCredentials.objects.get_or_create()

        self.contact_id = "mock-contact-uuid" if MOCK_XERO_API else LIVE_XERO_CONTACT_ID

        # Organisation with an existing Xero contact
        self.org, _ = Organisation.objects.update_or_create(
            org_id="S001",
            defaults=dict(
                name="Settlement Test Club",
                secretary=self.manager.alan,
                type="Club",
                club_email="settle@example.com",
                address1="1 Settlement St",
                suburb="Testville",
                state="NSW",
                postcode="2000",
                xero_contact_id=self.contact_id,
            ),
        )

        # Organisation with no Xero contact
        self.org_no_contact, _ = Organisation.objects.update_or_create(
            org_id="S002",
            defaults=dict(
                name="No Contact Settlement Club",
                secretary=self.manager.alan,
                type="Club",
                xero_contact_id="",
            ),
        )

    # -----------------------------------------------------------------------
    # Basic record creation
    # -----------------------------------------------------------------------

    def test_01_creates_pending_upload_record(self):
        """create_settlement_invoice creates a PENDING_UPLOAD XeroInvoice without POSTing to Xero"""
        xero = _make_api()
        with patch.object(xero, "xero_api_post") as mock_post:
            invoice = xero.create_settlement_invoice(
                organisation=self.org,
                bank_settlement_amount=250.00,
                reference="Settlement run 2026-03-15",
            )

        # A local record must exist
        saved = XeroInvoice.objects.filter(
            organisation=self.org, status=XeroInvoice.STATUS_PENDING_UPLOAD
        ).last()
        status = (
            invoice is not None
            and invoice.status == XeroInvoice.STATUS_PENDING_UPLOAD
            and saved is not None
            and not mock_post.called
        )
        self.manager.save_results(
            status=status,
            test_name="create_settlement_invoice: creates PENDING_UPLOAD record without calling Xero",
            test_description=(
                "Verify a local XeroInvoice is saved with PENDING_UPLOAD status "
                "and that no xero_api_post call is made for the invoice itself"
            ),
            output=(
                f"invoice.status={invoice.status if invoice else None!r}. "
                f"DB record found: {saved is not None}. "
                f"xero_api_post called: {mock_post.called}"
            ),
        )

    # -----------------------------------------------------------------------
    # Payload structure
    # -----------------------------------------------------------------------

    def test_02_payload_structure(self):
        """upload_payload has correct Type, InvoiceNumber, Status, LineItems, and AccountCode"""
        if _skip_in_live_mode(
            self.manager, "create_settlement_invoice: payload structure"
        ):
            return

        test_date = date(2025, 3, 31)
        xero = _make_api()
        invoice = xero.create_settlement_invoice(
            organisation=self.org,
            bank_settlement_amount=123.45,
            reference="Test payload ref",
            invoice_date=test_date,
        )

        payload = invoice.upload_payload if invoice else {}
        inv_data = (payload.get("Invoices") or [{}])[0]
        line_item = (inv_data.get("LineItems") or [{}])[0]

        status = (
            invoice is not None
            and inv_data.get("Type") == "ACCPAY"
            and inv_data.get("InvoiceNumber", "").startswith("MyABF-")
            and inv_data.get("Status") == "AUTHORISED"
            and inv_data.get("LineAmountTypes") == "Inclusive"
            and inv_data.get("Date") == "2025-03-31"
            and line_item.get("UnitAmount") == 123.45
            and line_item.get("AccountCode") == XERO_PAYABLE_ACCOUNT_CODE
        )
        self.manager.save_results(
            status=status,
            test_name="create_settlement_invoice: payload structure",
            test_description=(
                "Verify upload_payload contains Type=ACCPAY, InvoiceNumber starting with MyABF-, "
                "Status=AUTHORISED, LineAmountTypes=Inclusive, Date=invoice_date, correct UnitAmount and AccountCode"
            ),
            output=(
                f"Type={inv_data.get('Type')!r}. "
                f"InvoiceNumber={inv_data.get('InvoiceNumber')!r}. "
                f"Status={inv_data.get('Status')!r}. "
                f"LineAmountTypes={inv_data.get('LineAmountTypes')!r}. "
                f"Date={inv_data.get('Date')!r}. "
                f"UnitAmount={line_item.get('UnitAmount')!r}. "
                f"AccountCode={line_item.get('AccountCode')!r}"
            ),
        )

    # -----------------------------------------------------------------------
    # cobalt_reference format
    # -----------------------------------------------------------------------

    def test_03_cobalt_reference_format(self):
        """cobalt_reference matches MyABF-{12 uppercase hex chars}"""
        if _skip_in_live_mode(
            self.manager, "create_settlement_invoice: cobalt_reference format"
        ):
            return

        xero = _make_api()
        invoice = xero.create_settlement_invoice(
            organisation=self.org,
            bank_settlement_amount=50.00,
            reference="Format test",
        )

        ref = invoice.cobalt_reference if invoice else ""
        matches = bool(re.match(r"^MyABF-[0-9A-F]{12}$", ref))
        self.manager.save_results(
            status=matches,
            test_name="create_settlement_invoice: cobalt_reference format",
            test_description=(
                "Verify cobalt_reference matches the pattern MyABF-[0-9A-F]{12} "
                "(uppercase hex, 12 chars)"
            ),
            output=f"cobalt_reference={ref!r}. Matches pattern: {matches}",
        )

    # -----------------------------------------------------------------------
    # On-demand contact creation
    # -----------------------------------------------------------------------

    def test_04_creates_contact_when_missing(self):
        """create_settlement_invoice creates a Xero contact when org has none"""
        # Reset so the contact creation path is exercised
        self.org_no_contact.xero_contact_id = ""
        self.org_no_contact.save()

        mock_response = {"Contacts": [{"ContactID": "new-contact-uuid"}]}
        xero = _make_api()
        with _patch_post(xero, mock_response):
            invoice = xero.create_settlement_invoice(
                organisation=self.org_no_contact,
                bank_settlement_amount=100.00,
                reference="Contact creation test",
            )

        self.org_no_contact.refresh_from_db()
        if MOCK_XERO_API:
            status = (
                invoice is not None
                and invoice.status == XeroInvoice.STATUS_PENDING_UPLOAD
                and self.org_no_contact.xero_contact_id == "new-contact-uuid"
            )
            output = (
                f"invoice.status={invoice.status if invoice else None!r}. "
                f"xero_contact_id={self.org_no_contact.xero_contact_id!r}"
            )
        else:
            status = invoice is not None and bool(self.org_no_contact.xero_contact_id)
            output = f"xero_contact_id={self.org_no_contact.xero_contact_id!r}"

        self.manager.save_results(
            status=status,
            test_name="create_settlement_invoice: creates contact when org has none",
            test_description=(
                "Verify a Xero contact is created on demand and the ContactID is saved "
                "on the Organisation before the invoice record is queued"
            ),
            output=output,
        )

    def test_05_returns_none_when_contact_creation_fails(self):
        """create_settlement_invoice returns None and creates no invoice when contact creation fails"""
        if _skip_in_live_mode(
            self.manager,
            "create_settlement_invoice: returns None on contact creation failure",
        ):
            return

        self.org_no_contact.xero_contact_id = ""
        self.org_no_contact.save()

        count_before = XeroInvoice.objects.filter(
            organisation=self.org_no_contact
        ).count()

        xero = _make_api()
        with patch.object(xero, "xero_api_post", return_value={}):
            invoice = xero.create_settlement_invoice(
                organisation=self.org_no_contact,
                bank_settlement_amount=100.00,
                reference="Should fail",
            )

        count_after = XeroInvoice.objects.filter(
            organisation=self.org_no_contact
        ).count()
        status = invoice is None and count_after == count_before
        self.manager.save_results(
            status=status,
            test_name="create_settlement_invoice: returns None when contact creation fails",
            test_description=(
                "Verify None is returned and no XeroInvoice record is created "
                "when create_organisation_contact returns None (empty Xero response)"
            ),
            output=(
                f"Returned: {invoice!r}. "
                f"Invoice count before: {count_before}, after: {count_after}"
            ),
        )

    # -----------------------------------------------------------------------
    # Field values
    # -----------------------------------------------------------------------

    def test_06_amount_and_fields(self):
        """create_settlement_invoice sets correct amount, reference, type, and dates"""
        if _skip_in_live_mode(
            self.manager, "create_settlement_invoice: amount and fields"
        ):
            return

        xero = _make_api()
        invoice = xero.create_settlement_invoice(
            organisation=self.org,
            bank_settlement_amount=999.99,
            reference="Fields check ref",
        )

        today = date.today()
        status = (
            invoice is not None
            and float(invoice.amount) == 999.99
            and invoice.reference == "Fields check ref"
            and invoice.invoice_type == "ACCPAY"
            and invoice.date == today
            and invoice.due_date == today
        )
        self.manager.save_results(
            status=status,
            test_name="create_settlement_invoice: amount, reference, type, and dates",
            test_description=(
                "Verify amount, reference, invoice_type=ACCPAY, date=today, "
                "and due_date=today are all set correctly on the XeroInvoice record"
            ),
            output=(
                f"amount={invoice.amount if invoice else None!r}. "
                f"reference={invoice.reference if invoice else None!r}. "
                f"invoice_type={invoice.invoice_type if invoice else None!r}. "
                f"date={invoice.date if invoice else None!r}. "
                f"due_date={invoice.due_date if invoice else None!r}"
            ),
        )


# =============================================================================
# Notes on running these tests in live mode (MOCK_XERO_API = False)
# =============================================================================
#
# These tests follow the same live-mode guidelines as unit_test_xero_api.py.
# In particular:
#
# - Use a Xero demo/sandbox company — never real accounting data.
# - Set LIVE_XERO_CONTACT_ID to a valid Contact UUID in your demo company so
#   test_01, test_04 (org with existing contact) run correctly.
# - API calls create XeroInvoice rows in the database (rolled back by Django's
#   test transaction) and PENDING_UPLOAD records (no Xero API calls for the
#   invoice itself — the upload is always deferred to the management command).
# - Tests 02, 03, 05, 06 inspect local data only and are always mocked.
# - Run: python manage.py run_tests_unit --app xero
