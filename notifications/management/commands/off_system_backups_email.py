import subprocess

from django.core.management.base import BaseCommand
from django.utils.safestring import mark_safe

from notifications.views.core import send_cobalt_email_with_template

SESSION_LOG = "/tmp/off_system_backups.log"


# This is created by off_system_backup_cron.sh
class Command(BaseCommand):
    """send notifications about the off system backups"""

    def add_arguments(self, parser):
        # Positional arguments

        parser.add_argument("--status", help="Success or Failure")
        parser.add_argument("--subject", help="High level message")

    def handle(self, *args, **options):

        status = options["status"]
        subject = options["subject"]

        if status == "success":
            sender = "Backup Success<noreply@myabf.com.au>"
        else:
            sender = "Backup Failed<noreply@myabf.com.au>"

        tail = subprocess.run(["tail", "-100", SESSION_LOG], stdout=subprocess.PIPE)
        log_data = tail.stdout.decode("utf-8")
        email_body = f"""
        <h3>Last lines of the log file</h3>

        <pre>
        {log_data}
        </pre>
"""

        context = {
            "subject": subject,
            "email_body": mark_safe(email_body),
        }

        send_cobalt_email_with_template(
            "m@rkguthrie.com",
            context,
            priority="now",
            sender=sender,
        )
        self.stdout.write(self.style.SUCCESS("Email sent"))
