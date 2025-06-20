from django.core.management.base import BaseCommand

from notifications.views.core import send_cobalt_email_with_template


class Command(BaseCommand):
    """send notifications about the off system backups"""

    def handle(self, *args, **options):

        send_cobalt_email_with_template(
            "m@rkguthrie.com", {"subject": "Off System Backups"}, priority="now"
        )
        self.stdout.write(self.style.SUCCESS("Email sent"))
