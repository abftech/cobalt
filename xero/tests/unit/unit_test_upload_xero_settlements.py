"""Unit tests for the upload_xero_settlements management command helpers.

Tests the module-level functions _find_in_xero, _upload_invoice, and
_extract_xero_error directly — no need to invoke the full management command.

All tests run in mock mode by default (MOCK_XERO_API = True).
"""

from datetime import date
from unittest.mock import patch

from organisations.models import Organisation
from tests.test_manager import CobaltTestManagerUnit
from xero.management.commands.upload_xero_settlements import (
    MAX_UPLOAD_ATTEMPTS,
    _extract_xero_error,
    _find_in_xero,
    _upload_invoice,
)
from xero.models import XeroCredentials, XeroInvoice

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

MOCK_XERO_API = True


def _make_api():
    """Return a XeroApi instance, ensuring a credentials row exists."""
    from xero.core import XeroApi

    XeroCredentials.objects.get_or_create()
    return XeroApi()


class UploadXeroSettlementsTests:
    """Unit tests for module-level helpers in upload_xero_settlements.py.

    Covers: _find_in_xero (found / not found), _extract_xero_error (root /
    elements / fallback), and _upload_invoice (success, idempotency, failure,
    max attempts, null UUID, error message preservation).
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager

        XeroCredentials.objects.get_or_create()

        self.org = Organisation(
            org_id="U001",
            name="Upload Test Club",
            secretary=self.manager.alan,
            type="Club",
            xero_contact_id="mock-contact-uuid",
        )
        self.org.save()

    def _make_invoice(self, upload_attempts=0) -> XeroInvoice:
        """Create and save a fresh PENDING_UPLOAD XeroInvoice for each test."""
        invoice = XeroInvoice(
            organisation=self.org,
            xero_invoice_id="",
            invoice_type="ACCPAY",
            amount=500.00,
            status=XeroInvoice.STATUS_PENDING_UPLOAD,
            reference="Test settlement",
            cobalt_reference="MyABF-TESTREF00001",
            upload_payload={"Invoices": [{"Type": "ACCPAY"}]},
            upload_attempts=upload_attempts,
            date=date.today(),
            due_date=date.today(),
        )
        invoice.save()
        return invoice

    # -----------------------------------------------------------------------
    # _find_in_xero
    # -----------------------------------------------------------------------

    def test_01_find_returns_invoice_dict(self):
        """_find_in_xero returns the first invoice dict when Xero finds a match"""
        xero = _make_api()
        mock_response = {
            "Invoices": [
                {"InvoiceID": "xero-id-abc", "InvoiceNumber": "MyABF-TESTREF00001"}
            ]
        }
        with patch.object(xero, "xero_api_get", return_value=mock_response):
            result = _find_in_xero(xero, "MyABF-TESTREF00001")

        status = result is not None and result.get("InvoiceID") == "xero-id-abc"
        self.manager.save_results(
            status=status,
            test_name="_find_in_xero: returns invoice dict when found",
            test_description=(
                "Verify _find_in_xero returns the first invoice dict from the Xero "
                "response when a matching InvoiceNumber is found"
            ),
            output=f"result={result!r}",
        )

    def test_02_find_returns_none_when_not_found(self):
        """_find_in_xero returns None when Xero returns an empty Invoices list"""
        xero = _make_api()
        with patch.object(xero, "xero_api_get", return_value={"Invoices": []}):
            result = _find_in_xero(xero, "MyABF-DOESNOTEXIST")

        self.manager.save_results(
            status=result is None,
            test_name="_find_in_xero: returns None when not found",
            test_description=(
                "Verify _find_in_xero returns None when Xero returns an empty Invoices list"
            ),
            output=f"result={result!r}",
        )

    # -----------------------------------------------------------------------
    # _extract_xero_error
    # -----------------------------------------------------------------------

    def test_03_extract_from_response_root(self):
        """_extract_xero_error extracts ValidationErrors from the top-level response"""
        response = {"ValidationErrors": [{"Message": "Bad date format"}]}
        result = _extract_xero_error(response, {})

        status = "Bad date format" in result
        self.manager.save_results(
            status=status,
            test_name="_extract_xero_error: extracts from top-level ValidationErrors",
            test_description=(
                "Verify the error message from response['ValidationErrors'] is returned"
            ),
            output=f"result={result!r}",
        )

    def test_04_extract_from_elements(self):
        """_extract_xero_error extracts ValidationErrors from Elements[0]"""
        response = {
            "Elements": [{"ValidationErrors": [{"Message": "Bad account code"}]}]
        }
        result = _extract_xero_error(response, {})

        status = "Bad account code" in result
        self.manager.save_results(
            status=status,
            test_name="_extract_xero_error: extracts from Elements[0].ValidationErrors",
            test_description=(
                "Verify the error message is extracted from Elements[0]['ValidationErrors'] "
                "when the top-level response has no ValidationErrors"
            ),
            output=f"result={result!r}",
        )

    def test_05_extract_fallback(self):
        """_extract_xero_error returns a non-empty fallback string when no ValidationErrors exist"""
        result = _extract_xero_error({}, {})

        status = bool(result) and isinstance(result, str)
        self.manager.save_results(
            status=status,
            test_name="_extract_xero_error: returns non-empty fallback",
            test_description=(
                "Verify a non-empty string is returned when neither response nor "
                "invoice_data contain any ValidationErrors"
            ),
            output=f"result={result!r}",
        )

    # -----------------------------------------------------------------------
    # _upload_invoice
    # -----------------------------------------------------------------------

    def test_06_upload_success(self):
        """_upload_invoice sets AUTHORISED, xero_invoice_id, and clears upload_payload on success"""
        invoice = self._make_invoice()
        xero = _make_api()

        post_response = {
            "Invoices": [{"InvoiceID": "real-xero-id", "InvoiceNumber": "INV-001"}]
        }
        with patch.object(xero, "xero_api_get", return_value={"Invoices": []}):
            with patch.object(xero, "xero_api_post", return_value=post_response):
                _upload_invoice(xero, invoice, [])

        invoice.refresh_from_db()
        status = (
            invoice.status == "AUTHORISED"
            and invoice.xero_invoice_id == "real-xero-id"
            and invoice.invoice_number == "INV-001"
            and invoice.upload_payload is None
        )
        self.manager.save_results(
            status=status,
            test_name="_upload_invoice: success — AUTHORISED, xero_invoice_id set, payload cleared",
            test_description=(
                "Verify that on a successful POST the invoice status is AUTHORISED, "
                "xero_invoice_id and invoice_number are set, and upload_payload is cleared"
            ),
            output=(
                f"status={invoice.status!r}. "
                f"xero_invoice_id={invoice.xero_invoice_id!r}. "
                f"invoice_number={invoice.invoice_number!r}. "
                f"upload_payload={invoice.upload_payload!r}"
            ),
        )

    def test_07_upload_idempotency(self):
        """_upload_invoice marks AUTHORISED without calling POST when invoice is already in Xero"""
        invoice = self._make_invoice()
        xero = _make_api()

        already_in_xero = {
            "InvoiceID": "existing-xero-id",
            "InvoiceNumber": "INV-EXISTING",
        }
        with patch.object(
            xero, "xero_api_get", return_value={"Invoices": [already_in_xero]}
        ):
            with patch.object(xero, "xero_api_post") as mock_post:
                _upload_invoice(xero, invoice, [])

        invoice.refresh_from_db()
        status = (
            invoice.status == "AUTHORISED"
            and invoice.xero_invoice_id == "existing-xero-id"
            and not mock_post.called
        )
        self.manager.save_results(
            status=status,
            test_name="_upload_invoice: idempotency — AUTHORISED without POST when already in Xero",
            test_description=(
                "Verify that when the idempotency check finds the invoice already in Xero, "
                "it is marked AUTHORISED without making a POST call"
            ),
            output=(
                f"status={invoice.status!r}. "
                f"xero_invoice_id={invoice.xero_invoice_id!r}. "
                f"xero_api_post called: {mock_post.called}"
            ),
        )

    def test_08_upload_failure_increments_attempts(self):
        """_upload_invoice increments upload_attempts and resets to PENDING_UPLOAD on first failure"""
        invoice = self._make_invoice(upload_attempts=0)
        xero = _make_api()

        with patch.object(xero, "xero_api_get", return_value={"Invoices": []}):
            with patch.object(xero, "xero_api_post", side_effect=Exception("timeout")):
                _upload_invoice(xero, invoice, [])

        invoice.refresh_from_db()
        status = (
            invoice.upload_attempts == 1
            and invoice.upload_error == "timeout"
            and invoice.status == XeroInvoice.STATUS_PENDING_UPLOAD
        )
        self.manager.save_results(
            status=status,
            test_name="_upload_invoice: first failure increments attempts, resets to PENDING_UPLOAD",
            test_description=(
                "Verify upload_attempts is incremented, upload_error is saved, "
                "and status is reset to PENDING_UPLOAD (not UPLOAD_FAILED) on first failure"
            ),
            output=(
                f"upload_attempts={invoice.upload_attempts}. "
                f"upload_error={invoice.upload_error!r}. "
                f"status={invoice.status!r}"
            ),
        )

    def test_09_upload_failure_max_attempts(self):
        """_upload_invoice sets UPLOAD_FAILED after MAX_UPLOAD_ATTEMPTS failures"""
        invoice = self._make_invoice(upload_attempts=MAX_UPLOAD_ATTEMPTS - 1)
        xero = _make_api()

        with patch.object(xero, "xero_api_get", return_value={"Invoices": []}):
            with patch.object(
                xero, "xero_api_post", side_effect=Exception("final failure")
            ):
                _upload_invoice(xero, invoice, [])

        invoice.refresh_from_db()
        status = (
            invoice.status == XeroInvoice.STATUS_UPLOAD_FAILED
            and invoice.upload_attempts == MAX_UPLOAD_ATTEMPTS
        )
        self.manager.save_results(
            status=status,
            test_name=f"_upload_invoice: UPLOAD_FAILED after {MAX_UPLOAD_ATTEMPTS} attempts",
            test_description=(
                f"Verify status is set to UPLOAD_FAILED when upload_attempts reaches "
                f"MAX_UPLOAD_ATTEMPTS ({MAX_UPLOAD_ATTEMPTS})"
            ),
            output=(
                f"status={invoice.status!r}. "
                f"upload_attempts={invoice.upload_attempts} "
                f"(MAX_UPLOAD_ATTEMPTS={MAX_UPLOAD_ATTEMPTS})"
            ),
        )

    def test_10_upload_null_xero_id(self):
        """_upload_invoice treats a null/zero UUID from Xero as a failure"""
        invoice = self._make_invoice(upload_attempts=0)
        xero = _make_api()

        null_uuid = "00000000-0000-0000-0000-000000000000"
        post_response = {"Invoices": [{"InvoiceID": null_uuid}]}

        with patch.object(xero, "xero_api_get", return_value={"Invoices": []}):
            with patch.object(xero, "xero_api_post", return_value=post_response):
                _upload_invoice(xero, invoice, [])

        invoice.refresh_from_db()
        status = invoice.status != "AUTHORISED" and invoice.upload_attempts == 1
        self.manager.save_results(
            status=status,
            test_name="_upload_invoice: null UUID from Xero treated as failure",
            test_description=(
                "Verify that when Xero returns the all-zeros UUID the invoice is "
                "treated as a failed upload (attempts incremented, status not AUTHORISED)"
            ),
            output=(
                f"status={invoice.status!r}. "
                f"upload_attempts={invoice.upload_attempts}"
            ),
        )

    def test_11_upload_error_message_saved(self):
        """_upload_invoice saves the exception message in upload_error"""
        invoice = self._make_invoice(upload_attempts=0)
        xero = _make_api()

        with patch.object(xero, "xero_api_get", return_value={"Invoices": []}):
            with patch.object(
                xero, "xero_api_post", side_effect=ValueError("AccountCode invalid")
            ):
                _upload_invoice(xero, invoice, [])

        invoice.refresh_from_db()
        status = invoice.upload_error == "AccountCode invalid"
        self.manager.save_results(
            status=status,
            test_name="_upload_invoice: exception message saved in upload_error",
            test_description=(
                "Verify the str() of the raised exception is stored in upload_error"
            ),
            output=f"upload_error={invoice.upload_error!r}",
        )
