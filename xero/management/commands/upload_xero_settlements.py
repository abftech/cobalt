"""Management command to upload queued Xero settlement invoices.

Processes XeroInvoice records with status PENDING_UPLOAD, uploading each to the
Xero API with full idempotency (via the cobalt_reference / InvoiceNumber field),
crash recovery (UPLOADING status reconciliation on startup), and rate limiting.

Designed to run every 5 minutes via cron.
"""

import logging
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone

from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock
from xero.core import XeroApi
from xero.models import XeroInvoice

logger = logging.getLogger("cobalt")

MAX_UPLOAD_ATTEMPTS = 5
STALE_PENDING_HOURS = 24


class Command(BaseCommand):
    help = "Upload queued Xero settlement invoices (PENDING_UPLOAD) to Xero"

    def handle(self, *args, **options):
        logger.info("upload_xero_settlements starting")

        batch = BatchStatus.objects.create(command="upload_xero_settlements")
        summary_lines = []

        try:
            lock = CobaltLock("upload_xero_settlements", expiry=10)
            if not lock.get_lock():
                logger.info("upload_xero_settlements already running (locked), exiting")
                sys.exit(0)

            xero = XeroApi()
            processed = 0
            failed = 0

            # ------------------------------------------------------------------
            # STEP 1: Startup reconciliation — resolve any UPLOADING records left
            # by a previous crashed run.
            # ------------------------------------------------------------------
            uploading_records = XeroInvoice.objects.filter(
                status=XeroInvoice.STATUS_UPLOADING
            )
            uploading_count = uploading_records.count()
            if uploading_count:
                summary_lines.append(
                    f"Reconciling {uploading_count} UPLOADING record(s) from previous run..."
                )
                logger.info(
                    f"upload_xero_settlements: reconciling {uploading_count} UPLOADING record(s)"
                )

            for invoice in uploading_records:
                try:
                    found = _find_in_xero(xero, invoice.cobalt_reference)
                    if found:
                        xero_id = found.get("InvoiceID", "")
                        xero_number = found.get("InvoiceNumber", "")
                        invoice.xero_invoice_id = xero_id
                        invoice.invoice_number = xero_number
                        invoice.status = "AUTHORISED"
                        invoice.upload_payload = None
                        invoice.save(
                            update_fields=[
                                "xero_invoice_id",
                                "invoice_number",
                                "status",
                                "upload_payload",
                                "updated_at",
                            ]
                        )
                        summary_lines.append(
                            f"  Reconciled {invoice.cobalt_reference} → AUTHORISED ({xero_id})"
                        )
                        logger.info(
                            f"upload_xero_settlements: reconciled {invoice.cobalt_reference} found in Xero as {xero_id}"
                        )
                    else:
                        # Not found in Xero — the POST never completed; reset to PENDING_UPLOAD.
                        invoice.status = XeroInvoice.STATUS_PENDING_UPLOAD
                        invoice.save(update_fields=["status", "updated_at"])
                        summary_lines.append(
                            f"  Reset {invoice.cobalt_reference} to PENDING_UPLOAD (not found in Xero)"
                        )
                        logger.info(
                            f"upload_xero_settlements: {invoice.cobalt_reference} not found in Xero — reset to PENDING_UPLOAD"
                        )
                except Exception as exc:
                    logger.error(
                        f"upload_xero_settlements: error reconciling {invoice.cobalt_reference}: {exc}"
                    )
                    summary_lines.append(
                        f"  ERROR reconciling {invoice.cobalt_reference}: {exc}"
                    )

            # ------------------------------------------------------------------
            # STEP 2: Stale alert — warn about records stuck for > 24 hours.
            # ------------------------------------------------------------------
            stale_cutoff = timezone.now() - timezone.timedelta(
                hours=STALE_PENDING_HOURS
            )
            stale_records = XeroInvoice.objects.filter(
                status=XeroInvoice.STATUS_PENDING_UPLOAD,
                created_at__lt=stale_cutoff,
            )
            for stale in stale_records:
                logger.error(
                    f"upload_xero_settlements: STALE — {stale.cobalt_reference} has been "
                    f"PENDING_UPLOAD since {stale.created_at:%Y-%m-%d %H:%M} (>{STALE_PENDING_HOURS}h)"
                )

            # ------------------------------------------------------------------
            # STEP 3: Process each PENDING_UPLOAD record oldest-first.
            # ------------------------------------------------------------------
            pending = XeroInvoice.objects.filter(
                status=XeroInvoice.STATUS_PENDING_UPLOAD
            ).order_by("created_at")
            pending_count = pending.count()
            summary_lines.append(
                f"Found {pending_count} PENDING_UPLOAD invoice(s) to process."
            )

            for invoice in pending:
                try:
                    _upload_invoice(xero, invoice, summary_lines)
                    if invoice.status == "AUTHORISED":
                        processed += 1
                    elif invoice.status == XeroInvoice.STATUS_UPLOAD_FAILED:
                        failed += 1
                except Exception as exc:
                    logger.error(
                        f"upload_xero_settlements: unexpected error processing {invoice.cobalt_reference}: {exc}"
                    )
                    summary_lines.append(
                        f"  UNEXPECTED ERROR for {invoice.cobalt_reference}: {exc}"
                    )
                    failed += 1

            # ------------------------------------------------------------------
            # STEP 4: Report any permanently failed records.
            # ------------------------------------------------------------------
            upload_failed_records = XeroInvoice.objects.filter(
                status=XeroInvoice.STATUS_UPLOAD_FAILED
            )
            if upload_failed_records.exists():
                summary_lines.append(
                    f"\nUPLOAD_FAILED records ({upload_failed_records.count()}) — manual intervention required:"
                )
                for rec in upload_failed_records:
                    summary_lines.append(
                        f"  [{rec.cobalt_reference}] {rec.organisation.name}: {rec.upload_error}"
                    )
                    logger.error(
                        f"upload_xero_settlements: UPLOAD_FAILED {rec.cobalt_reference} "
                        f"({rec.organisation.name}): {rec.upload_error}"
                    )

            summary_lines.append(
                f"\nTotal: {processed} uploaded, {failed} failed, "
                f"{pending_count - processed - failed} unchanged"
            )

            lock.free_lock()
            lock.delete_lock()

        except Exception as e:
            logger.exception(
                "upload_xero_settlements failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("upload_xero_settlements finished")


def _find_in_xero(xero: XeroApi, cobalt_reference: str) -> dict | None:
    """Query Xero for an invoice by its InvoiceNumber (our cobalt_reference).

    Returns the invoice dict if found, None otherwise.
    """
    url = f"https://api.xero.com/api.xro/2.0/Invoices?InvoiceNumbers={cobalt_reference}"
    response = xero.xero_api_get(url)
    invoices = response.get("Invoices", [])
    if invoices:
        return invoices[0]
    return None


def _upload_invoice(xero: XeroApi, invoice: XeroInvoice, summary_lines: list) -> None:
    """Upload a single PENDING_UPLOAD invoice to Xero, with idempotency.

    Mutates the invoice record in-place (saving to DB). Appends a line to
    summary_lines describing the outcome.
    """
    ref = invoice.cobalt_reference

    # Idempotency check: has this already been created in Xero?
    found = _find_in_xero(xero, ref)
    if found:
        xero_id = found.get("InvoiceID", "")
        xero_number = found.get("InvoiceNumber", "")
        invoice.xero_invoice_id = xero_id
        invoice.invoice_number = xero_number
        invoice.status = "AUTHORISED"
        invoice.upload_payload = None
        invoice.save(
            update_fields=[
                "xero_invoice_id",
                "invoice_number",
                "status",
                "upload_payload",
                "updated_at",
            ]
        )
        summary_lines.append(
            f"  {ref}: already in Xero as {xero_id} — marked AUTHORISED"
        )
        logger.info(
            f"upload_xero_settlements: {ref} already in Xero ({xero_id}) — marked AUTHORISED"
        )
        return

    # Mark as UPLOADING before making the API call (crash recovery marker).
    invoice.status = XeroInvoice.STATUS_UPLOADING
    invoice.save(update_fields=["status", "updated_at"])

    try:
        response = xero.xero_api_post(
            "https://api.xero.com/api.xro/2.0/Invoices",
            invoice.upload_payload,
        )

        invoices = response.get("Invoices", [])
        xero_invoice_data = invoices[0] if invoices else {}
        xero_id = xero_invoice_data.get("InvoiceID", "")

        if not xero_id or xero_id == "00000000-0000-0000-0000-000000000000":
            # Xero returned a failure; extract validation error if possible.
            error_msg = _extract_xero_error(response, xero_invoice_data)
            raise ValueError(error_msg)

        xero_number = xero_invoice_data.get("InvoiceNumber", "")
        invoice.xero_invoice_id = xero_id
        invoice.invoice_number = xero_number
        invoice.status = "AUTHORISED"
        invoice.upload_payload = None
        invoice.save(
            update_fields=[
                "xero_invoice_id",
                "invoice_number",
                "status",
                "upload_payload",
                "updated_at",
            ]
        )
        summary_lines.append(f"  {ref}: uploaded → {xero_id}")
        logger.info(
            f"upload_xero_settlements: {ref} uploaded successfully as {xero_id}"
        )

        # For fee invoices, immediately record a payment to close the invoice (→ PAID).
        if invoice.auto_record_payment:
            try:
                amount_due = float(
                    xero_invoice_data.get("AmountDue", float(invoice.amount))
                )
                xero.create_payment(xero_id, amount_due)
                summary_lines.append(f"  {ref}: payment recorded → PAID")
                logger.info(f"upload_xero_settlements: payment recorded for {ref}")
            except Exception as pay_exc:
                logger.error(
                    f"upload_xero_settlements: payment failed for {ref}: {pay_exc}"
                )
                summary_lines.append(
                    f"  {ref}: AUTHORISED but payment failed — {pay_exc}"
                )

    except Exception as exc:
        invoice.upload_attempts += 1
        invoice.upload_error = str(exc)

        if invoice.upload_attempts >= MAX_UPLOAD_ATTEMPTS:
            invoice.status = XeroInvoice.STATUS_UPLOAD_FAILED
            invoice.save(
                update_fields=[
                    "status",
                    "upload_attempts",
                    "upload_error",
                    "updated_at",
                ]
            )
            summary_lines.append(
                f"  {ref}: UPLOAD_FAILED after {invoice.upload_attempts} attempt(s): {exc}"
            )
            logger.error(
                f"upload_xero_settlements: {ref} UPLOAD_FAILED after {invoice.upload_attempts} attempts: {exc}"
            )
        else:
            invoice.status = XeroInvoice.STATUS_PENDING_UPLOAD
            invoice.save(
                update_fields=[
                    "status",
                    "upload_attempts",
                    "upload_error",
                    "updated_at",
                ]
            )
            summary_lines.append(
                f"  {ref}: attempt {invoice.upload_attempts} failed — will retry: {exc}"
            )
            logger.warning(
                f"upload_xero_settlements: {ref} attempt {invoice.upload_attempts} failed: {exc}"
            )


def _extract_xero_error(response: dict, invoice_data: dict) -> str:
    """Extract a human-readable error message from a failed Xero invoice response."""
    for source in (response, invoice_data, *response.get("Elements", [])):
        errors = source.get("ValidationErrors", [])
        messages = [e["Message"] for e in errors if e.get("Message")]
        if messages:
            return "; ".join(messages)
    return f"Invoice creation failed: {response}"
