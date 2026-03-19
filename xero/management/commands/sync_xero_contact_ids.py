"""Management command to sync Xero ContactIDs into Cobalt Organisation records.

Fetches all active Xero contacts, matches them to Cobalt Organisations by name,
and writes the Xero ContactID back into Organisation.xero_contact_id.  Always
overwrites existing IDs so that stale or incorrect values are corrected.

Blocked from running on production.

Usage:
    python manage.py sync_xero_contact_ids

"""

import logging
import sys

from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from cobalt.settings import COBALT_HOSTNAME
from organisations.models import Organisation
from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock
from xero.core import XeroApi

logger = logging.getLogger("cobalt")

PRODUCTION_HOSTS = ["myabf.com.au", "www.myabf.com.au"]


class Command(BaseCommand):
    help = "Sync Xero ContactIDs into Cobalt Organisation records by matching on name"

    def handle(self, *args, **options):
        if COBALT_HOSTNAME in PRODUCTION_HOSTS:
            raise SuspiciousOperation(
                "sync_xero_contact_ids must not be run on production"
            )

        logger.info("sync_xero_contact_ids starting")

        batch = BatchStatus.objects.create(command="sync_xero_contact_ids")
        summary_lines = []

        try:
            lock = CobaltLock("sync_xero_contact_ids", expiry=10)
            if not lock.get_lock():
                logger.info("sync_xero_contact_ids already running (locked), exiting")
                sys.exit(0)

            xero = XeroApi()
            xero_contacts_raw = []
            page = 1
            while True:
                response = xero.xero_api_get(
                    "https://api.xero.com/api.xro/2.0/Contacts"
                    f"?where=ContactStatus%3D%3D%22ACTIVE%22&page={page}"
                )
                page_contacts = response.get("Contacts", []) if response else []
                if not page_contacts:
                    break
                xero_contacts_raw.extend(page_contacts)
                logger.info(f"Fetched page {page}: {len(page_contacts)} contacts")
                page += 1

            xero_lookup = {}
            for c in xero_contacts_raw:
                name = c.get("Name")
                contact_id = c.get("ContactID")
                if name and contact_id:
                    xero_lookup[name.lower().strip()] = contact_id

            orgs = Organisation.objects.all().order_by("name")

            xero_count = len(xero_lookup)
            org_count = orgs.count()
            summary_lines.append(f"Xero contacts fetched: {xero_count}")
            summary_lines.append(f"Cobalt organisations:  {org_count}")

            updated = 0
            already_correct = 0
            no_match = 0

            for org in orgs:
                contact_id = xero_lookup.get(org.name.lower().strip())
                if contact_id is None:
                    no_match += 1
                    logger.debug(f"No Xero match for org: {org.name}")
                elif org.xero_contact_id == contact_id:
                    already_correct += 1
                else:
                    org.xero_contact_id = contact_id
                    org.save(update_fields=["xero_contact_id"])
                    updated += 1
                    logger.info(f"Updated {org.name}: xero_contact_id = {contact_id}")

            summary_lines.append(f"  Updated:          {updated}")
            summary_lines.append(f"  Already correct:  {already_correct}")
            summary_lines.append(f"  No Xero match:    {no_match}")

            lock.free_lock()
            lock.delete_lock()

        except Exception as e:
            logger.exception("sync_xero_contact_ids failed with an unhandled exception")
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("sync_xero_contact_ids finished")
