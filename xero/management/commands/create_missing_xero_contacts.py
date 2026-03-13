"""Management command to create Xero contacts for organisations that are missing one.

Finds all Organisation records with no xero_contact_id and creates a Xero contact
for each one.  Safe to run repeatedly — organisations that already have a contact
are skipped.

Usage:
    python manage.py create_missing_xero_contacts

    # Dry run — reports what would be created without making any API calls:
    python manage.py create_missing_xero_contacts --dry-run

"""

import logging
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q

from organisations.models import Organisation
from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock
from xero.core import XeroApi

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    help = "Create Xero contacts for organisations that do not have one"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without making any Xero API calls",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        logger.info(f"create_missing_xero_contacts starting (dry_run={dry_run})")

        batch = BatchStatus.objects.create(command="create_missing_xero_contacts")
        summary_lines = []

        if dry_run:
            summary_lines.append("DRY RUN — no changes will be made.\n")

        try:
            lock = CobaltLock("create_missing_xero_contacts", expiry=30)
            if not lock.get_lock():
                logger.info(
                    "create_missing_xero_contacts already running (locked), exiting"
                )
                sys.exit(0)

            orgs = Organisation.objects.filter(
                Q(xero_contact_id__isnull=True) | Q(xero_contact_id="")
            ).order_by("name")

            total = orgs.count()
            summary_lines.append(f"Organisations missing a Xero contact: {total}")

            if total == 0:
                lock.free_lock()
                lock.delete_lock()
                batch.status = BatchStatus.STATUS_SUCCESS
                batch.summary = "\n".join(summary_lines)
                batch.save()
                logger.info("create_missing_xero_contacts finished — nothing to do")
                return

            if dry_run:
                for org in orgs:
                    summary_lines.append(f"  Would create: {org.name} (id={org.id})")
                lock.free_lock()
                lock.delete_lock()
                batch.status = BatchStatus.STATUS_SUCCESS
                batch.summary = "\n".join(summary_lines)
                batch.save()
                logger.info("create_missing_xero_contacts dry run finished")
                return

            xero = XeroApi()
            created = 0
            failed = 0

            for org in orgs:
                contact_id = xero.create_organisation_contact(org)
                if contact_id:
                    created += 1
                    summary_lines.append(
                        f"  Created: {org.name} → ContactID {contact_id}"
                    )
                    logger.info(f"Created Xero contact for {org.name}: {contact_id}")
                else:
                    failed += 1
                    summary_lines.append(f"  FAILED:  {org.name} (id={org.id})")
                    logger.warning(f"Failed to create Xero contact for {org.name}")

            summary_lines.append(
                f"\nTotal: {created} created, {failed} failed out of {total}"
            )

            lock.free_lock()
            lock.delete_lock()

        except Exception as e:
            logger.exception(
                "create_missing_xero_contacts failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("create_missing_xero_contacts finished")
