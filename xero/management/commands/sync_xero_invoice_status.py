"""Management command to sync local XeroInvoice statuses with Xero.

Finds all AUTHORISED invoices locally and checks their current status in Xero.

"""

import logging
import sys

from django.core.management.base import BaseCommand

from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock
from xero.core import XeroApi
from xero.models import XeroInvoice

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    help = (
        "Sync local XeroInvoice statuses with Xero (detects bank-reconciled payments)"
    )

    def handle(self, *args, **options):
        logger.info("Sync Xero invoice status starting")

        batch = BatchStatus.objects.create(command="sync_xero_invoice_status")
        summary_lines = []

        try:
            sync_lock = CobaltLock("sync_xero_invoice_status", expiry=10)
            if not sync_lock.get_lock():
                logger.info(
                    "Sync Xero invoice status already running (locked), exiting"
                )
                sys.exit(0)

            pending = XeroInvoice.objects.filter(status="AUTHORISED")
            total = pending.count()

            summary_lines.append(f"Found {total} AUTHORISED invoice(s) to check.")

            if total == 0:
                sync_lock.free_lock()
                sync_lock.delete_lock()
                batch.status = BatchStatus.STATUS_SUCCESS
                batch.summary = "\n".join(summary_lines)
                batch.save()
                logger.info("Sync Xero invoice status finished — nothing to do")
                return

            xero = XeroApi()
            updated = 0
            errors = 0

            for invoice in pending:
                try:
                    response = xero.get_invoice(invoice.xero_invoice_id)
                    invoices = response.get("Invoices", [])
                    if not invoices:
                        logger.warning(
                            f"No data returned from Xero for invoice {invoice.xero_invoice_id}"
                        )
                        summary_lines.append(
                            f"  WARNING: no Xero data for invoice {invoice.xero_invoice_id}"
                        )
                        errors += 1
                        continue

                    xero_data = invoices[0]
                    xero_status = xero_data.get("Status")
                    xero_number = xero_data.get("InvoiceNumber", "")
                    changed = False
                    update_fields = ["updated_at"]

                    if xero_status and xero_status != invoice.status:
                        old_status = invoice.status
                        invoice.status = xero_status
                        update_fields.append("status")
                        changed = True
                        logger.info(
                            f"Invoice {invoice.invoice_number} ({invoice.xero_invoice_id}): "
                            f"{old_status} -> {xero_status}"
                        )
                        summary_lines.append(
                            f"  {invoice.invoice_number}: {old_status} -> {xero_status}"
                        )

                    if xero_number and not invoice.invoice_number:
                        invoice.invoice_number = xero_number
                        update_fields.append("invoice_number")
                        changed = True
                        logger.info(
                            f"Invoice {invoice.xero_invoice_id}: backfilled number {xero_number}"
                        )
                        summary_lines.append(f"  Backfilled number: {xero_number}")

                    if changed:
                        invoice.save(update_fields=update_fields)
                        updated += 1

                except Exception as exc:
                    logger.error(
                        f"Failed to sync invoice {invoice.xero_invoice_id}: {exc}"
                    )
                    summary_lines.append(
                        f"  ERROR syncing invoice {invoice.xero_invoice_id}: {exc}"
                    )
                    errors += 1

            summary_lines.append(
                f"\nTotal: {updated} updated, {errors} errors, "
                f"{total - updated - errors} unchanged"
            )

            sync_lock.free_lock()
            sync_lock.delete_lock()

        except Exception as e:
            logger.exception(
                "Sync Xero invoice status failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("Sync Xero invoice status finished")
