from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now

from accounts.models import TeamMate
from events.models import Event, Congress, EventEntry, EventEntryPlayer, Session
from events.tests.integration.common_functions import (
    enter_event_and_check,
    enter_event_then_pay_and_check,
    test_create_congress,
    test_create_event,
)
from events.views.core import fix_closed_congress
from organisations.models import Organisation
from payments.views.core import update_account, get_balance
from tests.test_manager import CobaltTestManagerIntegration


class AutoClose:
    """Test scenarios for an event being auto closed"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager

        # Set up Congress
        org = Organisation.objects.filter(name="Fantasy Bridge Club").first()
        self.congress = test_create_congress("Auto Close Championships", org)

        # Set up event
        self.event = test_create_event("Death Duel", self.congress)

    def a1_enter_do_not_pay(self):
        """add an entry to an event but don't pay for it.
        Have the congress auto close and check what happens to that entry
        """

        # # Create event entry
        # event_entry = EventEntry(event=self.event, primary_entrant=self.manager.keith)
        # event_entry.save()
        #
        # # Create event entry player
        # event_entry_player = EventEntryPlayer(event_entry=event_entry, player=self.manager.keith, payment_type="my-system-dollars", entry_fee=10, payment_received=0)
        # event_entry_player.save()

        # Login Keith
        self.manager.login_user(self.manager.keith)

        self.manager.sleep()

        # set dates to be 4 months old so we can run the auto close
        ref_date = (now() - timedelta(weeks=18)).date()
        self.congress.start_date = ref_date
        self.congress.end_date = ref_date
        self.congress.save()
        self.event.start_date = ref_date
        self.event.end_date = ref_date
        self.event.denormalised_start_date = ref_date
        self.event.denormalised_end_date = ref_date

        self.event.save()
        session = Session.objects.filter(event=self.event).first()
        session.session_date = ref_date
        session.save()

        # Don't need to go through the logic to see if this needs fixed, just call the
        # function that fixes it
        fix_closed_congress(self.congress, self.manager.alan)
