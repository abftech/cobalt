"""

Temporary script to make sure the event_id on OrganisationTransaction marches the event.

Originally we didn't update this if an entry was moved, which didn't matter until
more detailed movement reports were implemented

"""

from datetime import timedelta

from django.core.management.base import BaseCommand

from events.models import EventEntryPlayer
from payments.models import OrganisationTransaction


class Command(BaseCommand):
    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("Checking event_entry_players..."))

        for event_entry_player in (
            EventEntryPlayer.objects.filter(payment_status="Paid")
            .filter(entry_complete_date__isnull=False)
            .filter(payment_type__in=["my-system-dollars", "their-system-dollars"])
            .order_by("-pk")
            .select_related("event_entry__event")
        ):
            min_date = event_entry_player.entry_complete_date - timedelta(seconds=5)
            max_date = event_entry_player.entry_complete_date + timedelta(seconds=5)
            matches = (
                OrganisationTransaction.objects.filter(
                    created_date__lt=max_date, created_date__gt=min_date
                )
                .filter(member=event_entry_player.paid_by)
                .filter(amount=event_entry_player.entry_fee)
            )

            if not matches:
                print(f"No match for {event_entry_player}")
                continue

            if matches[0].event_id != event_entry_player.event_entry.event_id:
                print(
                    f"Found - {event_entry_player.id=} - Event={event_entry_player.event_entry.event_id} - Payment={matches[0].id}"
                )
