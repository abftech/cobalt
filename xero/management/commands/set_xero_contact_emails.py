"""Management command to update all Xero contacts to use a single email address.

Finds all Organisation records with a xero_contact_id and updates the EmailAddress
field on the corresponding Xero contact to the value supplied via --email.

Usage:
    python manage.py set_xero_contact_emails --email invoices@example.com

    # Dry run — reports what would be updated without making any API calls:
    python manage.py set_xero_contact_emails --email invoices@example.com --dry-run

"""

import logging
import sys

from django.core.management.base import BaseCommand

from organisations.models import Organisation
from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock
from xero.core import XeroApi

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    help = "Update all Xero contacts to use a single email address"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Email address to set on every Xero contact",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be updated without making any Xero API calls",
        )

    def handle(self, *args, **options):
        email = options["email"]
        dry_run = options["dry_run"]
        logger.info(
            f"set_xero_contact_emails starting (email={email}, dry_run={dry_run})"
        )

        batch = BatchStatus.objects.create(command="set_xero_contact_emails")
        summary_lines = []

        if dry_run:
            summary_lines.append("DRY RUN — no changes will be made.\n")

        summary_lines.append(f"Target email: {email}\n")

        try:
            lock = CobaltLock("set_xero_contact_emails", expiry=30)
            if not lock.get_lock():
                logger.info("set_xero_contact_emails already running (locked), exiting")
                sys.exit(0)

            orgs = (
                Organisation.objects.exclude(xero_contact_id="")
                .exclude(xero_contact_id__isnull=True)
                .order_by("name")
            )

            total = orgs.count()
            summary_lines.append(f"Organisations with a Xero contact: {total}")

            if total == 0:
                lock.free_lock()
                lock.delete_lock()
                batch.status = BatchStatus.STATUS_SUCCESS
                batch.summary = "\n".join(summary_lines)
                batch.save()
                logger.info("set_xero_contact_emails finished — nothing to do")
                return

            if dry_run:
                for org in orgs:
                    summary_lines.append(
                        f"  Would update: {org.name} (ContactID={org.xero_contact_id})"
                    )
                lock.free_lock()
                lock.delete_lock()
                batch.status = BatchStatus.STATUS_SUCCESS
                batch.summary = "\n".join(summary_lines)
                batch.save()
                logger.info("set_xero_contact_emails dry run finished")
                return

            xero = XeroApi()
            updated = 0
            failed = 0

            for org in orgs:
                payload = {
                    "Contacts": [
                        {
                            "ContactID": org.xero_contact_id,
                            "EmailAddress": email,
                        }
                    ]
                }
                response = xero.xero_api_post(
                    "https://api.xero.com/api.xro/2.0/Contacts", payload
                )
                contacts = response.get("Contacts", [])
                if contacts:
                    updated += 1
                    summary_lines.append(
                        f"  Updated: {org.name} (ContactID={org.xero_contact_id})"
                    )
                    logger.info(f"Updated Xero contact email for {org.name} to {email}")
                else:
                    failed += 1
                    summary_lines.append(
                        f"  FAILED:  {org.name} (ContactID={org.xero_contact_id})"
                    )
                    logger.warning(
                        f"Failed to update Xero contact email for {org.name}: {response}"
                    )

            summary_lines.append(
                f"\nTotal: {updated} updated, {failed} failed out of {total}"
            )

            lock.free_lock()
            lock.delete_lock()

        except Exception as e:
            logger.exception(
                "set_xero_contact_emails failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("set_xero_contact_emails finished")
