"""Script to sanitise prod data so we can use it for testing"""

from django.core.exceptions import SuspiciousOperation
from post_office.models import Email, STATUS

from cobalt.settings import (
    COBALT_HOSTNAME,
)
from accounts.models import User
from django.core.management.base import BaseCommand

from events.models import Congress
from organisations.models import (
    MemberClubEmail,
    Visitor,
    Organisation,
    MemberClubDetails,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        print("Cleaning production data to use for testing")

        print("Deleting queued email...")
        Email.objects.exclude(status=STATUS.sent).exclude(status=STATUS.failed).delete()

        print("Changing email addresses...")
        User.objects.all().update(email="a@b.com")
        MemberClubEmail.objects.all().update(email="a@b.com")
        MemberClubDetails.objects.all().update(email="a@b.com")
        Visitor.objects.all().update(email="a@b.com")
        Organisation.objects.all().update(club_email="a@b.com")
        Congress.objects.all().update(contact_email="a@b.com")
