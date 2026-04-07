"""One-off test command for exercising the email batch system.

Usage examples:

  # Send a single-email batch (small):
  python manage.py test_email_batch send --email you@example.com

  # Send a batch with 10 recipients (all go to the same address):
  python manage.py test_email_batch send --email you@example.com --count 10

  # Trigger Post Office to flush its queue immediately:
  python manage.py test_email_batch dispatch

  # Check status of a previously sent batch:
  python manage.py test_email_batch status XXXX-XXXX-XXXX

"""

import logging

from django.core.management.base import BaseCommand, CommandError

from notifications.models import BatchID, Recipient, Snooper
from notifications.views.core import (
    send_cobalt_email_with_template,
    _finalise_email_batch,
)

logger = logging.getLogger("cobalt")

# Fake system numbers used for test recipients. High enough to never clash
# with real ABF membership numbers.
_FAKE_SYS_NUM_BASE = 99900000


class Command(BaseCommand):
    help = "Test email batch sending and check status"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        # ── send ─────────────────────────────────────────────────────────────
        send_parser = subparsers.add_parser("send", help="Create and send a test batch")
        send_parser.add_argument(
            "--email",
            required=True,
            help="Destination email address (all recipients use this address)",
        )
        send_parser.add_argument(
            "--count",
            type=int,
            default=1,
            help="Number of recipients to create (default: 1)",
        )
        send_parser.add_argument(
            "--name",
            default="Tester",
            help="First name used in each email (default: Tester)",
        )

        # ── dispatch ─────────────────────────────────────────────────────────
        subparsers.add_parser(
            "dispatch", help="Flush the Django Post Office queue immediately"
        )

        # ── status ────────────────────────────────────────────────────────────
        status_parser = subparsers.add_parser(
            "status", help="Report on a previously sent batch"
        )
        status_parser.add_argument(
            "batch_id", help="Batch ID string e.g. XXXX-XXXX-XXXX"
        )

    # ─────────────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        action = options["action"]
        if action == "send":
            self._send(options)
        elif action == "dispatch":
            self._dispatch()
        elif action == "status":
            self._status(options["batch_id"])

    # ─────────────────────────────────────────────────────────────────────────

    def _send(self, options):
        email_address = options["email"]
        count = options["count"]
        first_name = options["name"]

        if count < 1:
            raise CommandError("--count must be at least 1")

        subject = f"Test batch — {count} recipient{'s' if count != 1 else ''}"

        # Create the BatchID directly (no RBAC needed for a test script)
        batch = BatchID()
        batch.create_new()
        batch.batch_type = BatchID.BATCH_TYPE_ADMIN
        batch.batch_size = count
        batch.description = subject
        batch.state = BatchID.BATCH_STATE_WIP
        batch.save()

        self.stdout.write(f"\nBatch ID : {batch.batch_id}")
        self.stdout.write(f"Subject  : {subject}")
        self.stdout.write(f"Address  : {email_address}")
        self.stdout.write(f"Count    : {count}\n")

        # Create recipients and queue emails
        queued = 0
        for i in range(count):
            fake_sys_num = _FAKE_SYS_NUM_BASE + i

            recipient = Recipient(
                batch=batch,
                system_number=fake_sys_num,
                first_name=first_name,
                last_name=f"Recipient{i + 1}",
                email=email_address,
                include=True,
                initial=True,
            )
            recipient.save()

            context = {
                "subject": subject,
                "title": subject,
                "email_body": (
                    f"<p>This is test email {i + 1} of {count} "
                    f"in batch <strong>{batch.batch_id}</strong>.</p>"
                    f"<p>If you are seeing this, the email batch system is working correctly.</p>"
                ),
                "name": first_name,
            }

            ok = send_cobalt_email_with_template(
                to_address=email_address,
                context=context,
                batch_id=batch,
            )

            if ok:
                queued += 1
                self.stdout.write(f"  Queued email {i + 1}/{count}")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Email {i + 1}/{count} was skipped (bounce list?)"
                    )
                )

        # Mark the batch complete and clean up Recipient records
        _finalise_email_batch(batch, batch_size=count)

        self.stdout.write(
            self.style.SUCCESS(f"\n{queued}/{count} email(s) queued successfully.")
        )
        self.stdout.write(
            "\nEmails are queued in Django Post Office. Run the following to flush "
            "the queue immediately:\n"
            "  python manage.py test_email_batch dispatch\n"
        )
        self.stdout.write(
            "After sending, check status with:\n"
            f"  python manage.py test_email_batch status {batch.batch_id}\n"
        )
        from cobalt.settings import COBALT_HOSTNAME

        self.stdout.write("UI links (requires login):")
        self.stdout.write(
            f"  All emails for this batch : http://{COBALT_HOSTNAME}/notifications/admin/email/view-email-by-batch/{batch.id}"
        )
        self.stdout.write(
            f"  Batch send/queue status   : http://{COBALT_HOSTNAME}/notifications/email/watch_emails/{batch.batch_id}"
        )
        self.stdout.write(
            f"  Admin all-email list      : http://{COBALT_HOSTNAME}/notifications/admin/email/view-all\n"
        )

    # ─────────────────────────────────────────────────────────────────────────

    def _dispatch(self):
        from post_office.mail import send_queued

        self.stdout.write("Flushing Django Post Office queue…")
        send_queued(processes=1)
        self.stdout.write(self.style.SUCCESS("Done."))

    # ─────────────────────────────────────────────────────────────────────────

    def _status(self, batch_id_str):
        batch = BatchID.objects.filter(batch_id=batch_id_str).first()
        if not batch:
            raise CommandError(f"No batch found with id '{batch_id_str}'")

        snoopers = Snooper.objects.select_related("post_office_email").filter(
            batch_id=batch
        )
        total = snoopers.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING("No Snooper records found for this batch.")
            )
            self.stdout.write("Emails may still be queued — try dispatching first:")
            self.stdout.write("  python manage.py test_email_batch dispatch")
            return

        sent = snoopers.exclude(ses_sent_at=None).count()
        delivered = snoopers.exclude(ses_delivered_at=None).count()
        opened = snoopers.exclude(ses_last_opened_at=None).count()
        clicked = snoopers.exclude(ses_last_clicked_at=None).count()
        bounced = snoopers.exclude(ses_last_bounce_at=None).count()

        # Post Office status breakdown
        from post_office.models import Email as POEmail

        po_sent = snoopers.filter(post_office_email__status=0).count()
        po_failed = snoopers.filter(post_office_email__status=1).count()
        po_queued = snoopers.filter(post_office_email__status=2).count()

        self.stdout.write(f"\nBatch     : {batch.batch_id}")
        self.stdout.write(f"Subject   : {batch.description}")
        self.stdout.write(f"State     : {batch.get_state_display()}")
        self.stdout.write(f"Created   : {batch.created}\n")

        self.stdout.write("── Post Office (our queue) ──────────────────")
        self.stdout.write(f"  Total    : {total}")
        self.stdout.write(f"  Sent     : {po_sent}")
        self.stdout.write(f"  Failed   : {po_failed}")
        self.stdout.write(f"  Queued   : {po_queued}")

        self.stdout.write("\n── SES (AWS delivery events) ────────────────")
        self.stdout.write(f"  Accepted : {sent}")
        self.stdout.write(f"  Delivered: {delivered}")
        self.stdout.write(f"  Opened   : {opened}")
        self.stdout.write(f"  Clicked  : {clicked}")
        self.stdout.write(f"  Bounced  : {bounced}")

        if po_queued > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{po_queued} email(s) still in Post Office queue. "
                    "Run: python manage.py test_email_batch dispatch"
                )
            )

        if sent == 0 and po_queued == 0 and po_sent > 0:
            self.stdout.write(
                self.style.WARNING(
                    "\nSES has not reported back yet — "
                    "SES delivery events can take a few minutes to arrive."
                )
            )

        self.stdout.write("\n── Per-email detail ─────────────────────────")
        for snooper in snoopers.order_by("post_office_email__created"):
            po = snooper.post_office_email
            to = po.to[0] if po.to else "?"
            po_status = {0: "sent", 1: "failed", 2: "queued", 3: "requeued"}.get(
                po.status, str(po.status)
            )
            ses_summary = []
            if snooper.ses_sent_at:
                ses_summary.append(f"accepted {snooper.ses_sent_at:%H:%M:%S}")
            if snooper.ses_delivered_at:
                ses_summary.append(f"delivered {snooper.ses_delivered_at:%H:%M:%S}")
            if snooper.ses_last_opened_at:
                ses_summary.append(f"opened×{snooper.ses_open_count}")
            if snooper.ses_last_clicked_at:
                ses_summary.append(f"clicked×{snooper.ses_clicked_count}")
            if snooper.ses_last_bounce_at:
                ses_summary.append(f"BOUNCED ({snooper.ses_bounce_reason})")
            ses_str = " → ".join(ses_summary) if ses_summary else "no SES events yet"
            self.stdout.write(f"  [{po.id}] {to}  PO:{po_status}  SES:{ses_str}")
