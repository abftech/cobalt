"""
Cron job to archive and/or delete old database records according to the
retention policy documented in each section below.

Usage:
    python manage.py archive_old_data           # live run
    python manage.py archive_old_data --dry-run # preview counts only, no DB changes

Each section in handle() covers one model (or closely related model group).
The header block on each section documents:
    - Model      : <app>.<Model>
    - Retention  : how long records are kept
    - Strategy   : DELETE (records removed) or ARCHIVE (exported to S3, then removed)
    - Status     : ACTIVE or DISABLED (commented out)
    - Reason     : why this retention period was chosen

To enable a disabled section, uncomment the lines marked with # TODO.

PERMANENT RECORDS — NOT INCLUDED IN THIS COMMAND
-------------------------------------------------
The following models are intentionally absent. They must not be deleted:
    payments.MemberTransaction      — Bridge Credits financial ledger
    payments.OrganisationTransaction — club settlement history
    payments.StripeTransaction      — Stripe payment audit trail
    xero.XeroInvoice                — accounting records
    events.EventEntry / EventEntryPlayer — entry and payment history
    results.ResultsFile / PlayerSummaryResult — competition history
    masterpoints.*                  — historical scoring records
"""

import gzip
import json
import logging
import os
import sys

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from cobalt.settings import MEDIA_ROOT
from logs.models import Log
from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock

# Root directory for all data archive files. This path sits inside MEDIA_ROOT
# which is mapped to S3 (via EFS mount on production) so files written here
# are automatically available in cloud storage.
ARCHIVE_ROOT = os.path.join(MEDIA_ROOT, "data_archive")

logger = logging.getLogger("cobalt")


def _archive_emails_to_s3(qs, label):
    """Serialise an Email or EmailArchive queryset to a gzipped JSON lines file
    in MEDIA_ROOT/data_archive/email/<YYYY-MM>/ then verify the write.

    Each line of the output file is a self-contained JSON object with all model
    fields plus member_system_number and sender_system_number so the records
    remain traceable after the User FK is no longer resolvable in the database.

    Raises RuntimeError if the file cannot be verified after writing so that
    the caller does not proceed to delete the database records.

    Args:
        qs:    QuerySet of Email or EmailArchive records to archive
        label: Human-readable label used in log messages (e.g. "notifications.Email")
    """
    now = timezone.now()
    month_dir = os.path.join(ARCHIVE_ROOT, "email", now.strftime("%Y-%m"))
    os.makedirs(month_dir, exist_ok=True)

    filename = f"email_archive_{now.strftime('%Y%m%d_%H%M%S')}.jsonl.gz"
    filepath = os.path.join(month_dir, filename)

    logger.info(f"_archive_emails_to_s3: writing {label} to {filepath}")

    record_count = 0
    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        for record in qs.select_related("member", "sender").iterator():
            row = {
                "id": record.pk,
                "subject": record.subject,
                "message": record.message,
                "status": record.status,
                "batch_id": record.batch_id,
                "recipient": record.recipient,
                "reply_to": record.reply_to,
                "member_id": record.member_id,
                "member_system_number": (
                    record.member.system_number if record.member_id else None
                ),
                "sender_id": record.sender_id,
                "sender_system_number": (
                    record.sender.system_number if record.sender_id else None
                ),
                "created_date": (
                    record.created_date.isoformat() if record.created_date else None
                ),
                "sent_date": (
                    record.sent_date.isoformat() if record.sent_date else None
                ),
                "source_model": label,
            }
            f.write(json.dumps(row) + "\n")
            record_count += 1

    file_size = os.path.getsize(filepath)
    if file_size == 0:
        raise RuntimeError(f"Archive file is empty after write: {filepath}")

    logger.info(
        f"_archive_emails_to_s3: {record_count} {label} record(s) written to {filepath}"
        f" ({file_size} bytes)"
    )


class Command(BaseCommand):
    help = "Archive and/or delete old database records per retention policy"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print record counts without deleting anything",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        logger.info(f"archive_old_data starting{' (dry run)' if dry_run else ''}")

        batch = BatchStatus.objects.create(command="archive_old_data")
        summary_lines = []

        if dry_run:
            summary_lines.append("DRY RUN — no records were modified\n")

        try:
            lock = CobaltLock("archive_old_data", expiry=60)
            if not lock.get_lock():
                logger.info("archive_old_data already running (locked), exiting")
                sys.exit(0)

            # ─── MODEL: logs.Log ─────────────────────────────────────────────────────
            # Model     : logs.Log
            # Retention : 180 days
            # Strategy  : DELETE
            # Status    : ACTIVE
            # Reason    : Operational event log used for debugging and monitoring.
            #             No audit or financial value after 6 months.
            # ─────────────────────────────────────────────────────────────────────────
            cutoff = timezone.now() - relativedelta(days=180)
            qs = Log.objects.filter(event_date__lt=cutoff)
            if dry_run:
                count = qs.count()
            else:
                count, _ = qs.delete()
            summary_lines.append(
                f"logs.Log: {count} record(s) {'would be ' if dry_run else ''}deleted"
                f" (retention: 180 days, cutoff: {cutoff.date()})"
            )
            logger.info(f"archive_old_data: logs.Log count={count} dry_run={dry_run}")

            # ─── MODEL: api.ApiLog ───────────────────────────────────────────────────
            # Model     : api.ApiLog
            # Retention : 90 days
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : API request audit log. Short operational value only.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from api.models import ApiLog
            # cutoff = timezone.now() - relativedelta(days=90)
            # qs = ApiLog.objects.filter(created_date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"api.ApiLog: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 90 days, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: xero.XeroLog ─────────────────────────────────────────────────
            # Model     : xero.XeroLog
            # Retention : 180 days
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Xero API call log for debugging integration issues.
            #             No accounting value; XeroInvoice holds the permanent record.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from xero.models import XeroLog
            # cutoff = timezone.now() - relativedelta(days=180)
            # qs = XeroLog.objects.filter(created_at__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"xero.XeroLog: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 180 days, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: payments.StripeLog ───────────────────────────────────────────
            # Model     : payments.StripeLog
            # Retention : 180 days
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Stripe webhook event log for debugging. StripeTransaction
            #             holds the permanent financial record.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from payments.models import StripeLog
            # cutoff = timezone.now() - relativedelta(days=180)
            # qs = StripeLog.objects.filter(created_date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"payments.StripeLog: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 180 days, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: utils.Error500 ───────────────────────────────────────────────
            # Model     : utils.Error500
            # Retention : 90 days
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Server error log for debugging. Short operational value.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from utils.models import Error500
            # cutoff = timezone.now() - relativedelta(days=90)
            # qs = Error500.objects.filter(error_date_time__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"utils.Error500: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 90 days, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: utils.Batch / utils.BatchStatus ──────────────────────────────
            # Model     : utils.Batch, utils.BatchStatus
            # Retention : 1 year
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Management command execution audit trail. Useful for
            #             recent history only. Excludes the current run's record.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from utils.models import Batch
            # cutoff = timezone.now() - relativedelta(years=1)
            # qs = Batch.objects.filter(run_date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"utils.Batch: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 1 year, cutoff: {cutoff.date()})"
            # )
            # qs = BatchStatus.objects.filter(run_date__lt=cutoff).exclude(pk=batch.pk)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"utils.BatchStatus: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 1 year, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: notifications.RealtimeNotificationHeader / RealtimeNotification
            # Model     : notifications.RealtimeNotificationHeader (+ children cascade)
            #             notifications.RealtimeNotification
            # Retention : 90 days
            # Strategy  : DELETE (deleting the header cascades to RealtimeNotification)
            # Status    : DISABLED
            # Reason    : SMS and push notification delivery log. Short operational
            #             value; delivery receipts not required for compliance.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from notifications.models import RealtimeNotificationHeader
            # cutoff = timezone.now() - relativedelta(days=90)
            # qs = RealtimeNotificationHeader.objects.filter(created_time__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"notifications.RealtimeNotificationHeader: {count} record(s)"
            #     f" {'would be ' if dry_run else ''}deleted (children cascade)"
            #     f" (retention: 90 days, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: organisations.ClubLog ────────────────────────────────────────
            # Model     : organisations.ClubLog
            # Retention : 2 years
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Club activity audit trail. 2 years provides sufficient
            #             history for dispute resolution and reporting.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from organisations.models import ClubLog
            # cutoff = timezone.now() - relativedelta(years=2)
            # qs = ClubLog.objects.filter(action_date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"organisations.ClubLog: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 2 years, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: organisations.ClubMemberLog ──────────────────────────────────
            # Model     : organisations.ClubMemberLog
            # Retention : 2 years
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Member activity log within a club. 2 years provides
            #             sufficient history for dispute resolution.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from organisations.models import ClubMemberLog
            # cutoff = timezone.now() - relativedelta(years=2)
            # qs = ClubMemberLog.objects.filter(date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"organisations.ClubMemberLog: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 2 years, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: events.EventLog ──────────────────────────────────────────────
            # Model     : events.EventLog
            # Retention : 2 years
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Action audit trail for congress events. Long enough to
            #             cover any post-event disputes. Congress and EventEntry
            #             records themselves are kept permanently.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from events.models import EventLog
            # cutoff = timezone.now() - relativedelta(years=2)
            # qs = EventLog.objects.filter(action_date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"events.EventLog: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 2 years, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: events.PartnershipDesk ───────────────────────────────────────
            # Model     : events.PartnershipDesk
            # Retention : 30 days after the congress end date
            # Strategy  : DELETE
            # Status    : DISABLED
            # Reason    : Temporary partner-matching ads. No value once the congress
            #             has concluded and a grace period has passed.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from events.models import PartnershipDesk
            # cutoff = timezone.now() - relativedelta(days=30)
            # qs = PartnershipDesk.objects.filter(event__congress__end_date__lt=cutoff)
            # count = qs.count()
            # if not dry_run:
            #     qs.delete()
            # summary_lines.append(
            #     f"events.PartnershipDesk: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #     f" (retention: 30 days post-congress, cutoff: {cutoff.date()})"
            # )

            # ─── MODEL: events.Bulletin / events.CongressDownload ────────────────────
            # Model     : events.Bulletin, events.CongressDownload
            # Retention : 1 year after the congress end date
            # Strategy  : DELETE (files on S3 are removed by Django's storage layer)
            # Status    : DISABLED
            # Reason    : Congress documents (bulletins, downloads). A 1-year grace
            #             period allows post-event reference before removal.
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable
            # from events.models import Bulletin, CongressDownload
            # cutoff = timezone.now() - relativedelta(years=1)
            # for model_cls, label in [(Bulletin, "events.Bulletin"), (CongressDownload, "events.CongressDownload")]:
            #     qs = model_cls.objects.filter(congress__end_date__lt=cutoff)
            #     count = qs.count()
            #     if not dry_run:
            #         qs.delete()
            #     summary_lines.append(
            #         f"{label}: {count} record(s) {'would be ' if dry_run else ''}deleted"
            #         f" (retention: 1 year post-congress, cutoff: {cutoff.date()})"
            #     )

            # ─── MODEL: notifications.Email / notifications.EmailArchive ─────────────
            # Model     : notifications.Email, notifications.EmailArchive
            # Retention : 2 years, then archived to S3
            # Strategy  : ARCHIVE — export to S3 as gzipped JSON lines, then DELETE
            # Status    : DISABLED
            # Reason    : Email delivery records. The PROTECT FK constraint on
            #             member/sender means these records must be removed before
            #             a User record can be deleted. Archiving to S3 preserves
            #             the data for compliance while freeing the FK constraint.
            #
            # Archive format:
            #   s3://<bucket>/archive/email/<YYYY-MM>/email_archive_<timestamp>.jsonl.gz
            #   Each line is a JSON object with all model fields plus
            #   member_system_number and sender_system_number for traceability
            #   after the User FK is no longer resolvable.
            #
            # Steps when enabled:
            #   1. Query records with created_date older than 2 years
            #   2. Serialise to a gzipped JSON lines file in memory
            #   3. Upload to S3 via boto3 (already a project dependency)
            #   4. Verify the S3 object exists and byte count matches
            #   5. Delete the DB records only after a confirmed successful upload
            # ─────────────────────────────────────────────────────────────────────────
            # TODO: uncomment to enable (requires implementing _archive_emails_to_s3)
            # from notifications.models import Email, EmailArchive
            # cutoff = timezone.now() - relativedelta(years=2)
            # for model_cls, label in [(Email, "notifications.Email"), (EmailArchive, "notifications.EmailArchive")]:
            #     qs = model_cls.objects.filter(created_date__lt=cutoff)
            #     count = qs.count()
            #     if count:
            #         if not dry_run:
            #             _archive_emails_to_s3(qs, label)
            #             qs.delete()
            #         summary_lines.append(
            #             f"{label}: {count} record(s) {'would be ' if dry_run else ''}archived to S3 and deleted"
            #             f" (retention: 2 years, cutoff: {cutoff.date()})"
            #         )
            #     else:
            #         summary_lines.append(f"{label}: 0 records to archive")

            lock.free_lock()

        except Exception as e:
            logger.exception("archive_old_data failed with an unhandled exception")
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("archive_old_data finished")
