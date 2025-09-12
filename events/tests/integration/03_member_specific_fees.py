from datetime import timedelta
from time import sleep

from django.urls import reverse
from django.utils.timezone import now

from accounts.models import TeamMate, User
from events.forms import EventForm
from events.models import (
    Event,
    Congress,
    EventEntry,
    EventEntryPlayer,
    Session,
    BasketItem,
    EVENT_PLAYER_FORMAT,
    EVENT_PLAYER_FORMAT_SIZE,
)
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

EXPECTED_ENTRY_FEE = 100
EXPECTED_MEMBER_ENTRY_FEE = 200


def _change_data_and_check(congress, event, manager, test_name, check_member_fee=True):
    """helper to test the form and the UI for data changes. We change the event type to trigger the code
    nothing else (especially entry fees) should be changed
    """

    # Loop through different player numbers
    for player_format_tuple in EVENT_PLAYER_FORMAT:
        # for player_format_tuple in [("Teams", "xx")]:

        player_format = player_format_tuple[0]

        # Teams of 3 doesn't seem to be supported for this
        if player_format == "Teams of 3":
            continue

        event.player_format = player_format
        event.save()
        number_of_players = EVENT_PLAYER_FORMAT_SIZE[player_format]
        # For teams hard code to 4
        if player_format == "Teams":
            number_of_players = 4

        # set the fees
        event.entry_fee = EXPECTED_ENTRY_FEE
        event.member_entry_fee = EXPECTED_MEMBER_ENTRY_FEE
        event.save()

        # Test the form

        # make a random change
        event_type = "Senior" if event.event_type == "Rookies" else "Rookies"

        form_data = {
            "event_name": "Team",
            "event_type": event_type,
            "player_format": "Teams",
            "entry_youth_payment_discount": 0,
            "list_priority_order": 0,
            "member_entry_fee": EXPECTED_MEMBER_ENTRY_FEE / number_of_players,
        }
        event_form = EventForm(data=form_data, instance=event)

        status = event_form.is_valid()

        manager.save_results(
            status=status,
            test_name=f"Edit event and check fees - validate form - {player_format} - {test_name}",
            test_description="Edit an event, through the form directly. Check form status.",
            output=f"Form is_valid={status}. Form errors: {event_form.errors}",
        )

        # reload event
        event = Event.objects.get(pk=event.id)

        status = event.entry_fee == EXPECTED_ENTRY_FEE

        if check_member_fee:
            status = status and event.member_entry_fee == EXPECTED_MEMBER_ENTRY_FEE

        manager.save_results(
            status=status,
            test_name=f"Edit event and check fees through form - {player_format} - {test_name}",
            test_description="Edit an event, through the form directly. Check the entry fees do not get corrupted.",
            output=f"{check_member_fee=} {EXPECTED_ENTRY_FEE=} {event.entry_fee=} {EXPECTED_MEMBER_ENTRY_FEE=} {event.member_entry_fee=}",
        )

        # Do it through the UI
        manager.driver.get(
            f"{manager.base_url}/events/congress-builder/create/edit-event/{congress.id}/{event.id}"
        )

        # make a random change
        event_type = "Senior" if event.event_type == "Rookies" else "Rookies"

        manager.selenium_wait_for_select_and_pick_an_option("id_event_type", event_type)

        manager.selenium_wait_for_clickable("id_save").click()

        sleep(1)

        # reload event
        event = Event.objects.get(pk=event.id)

        status = event.entry_fee == EXPECTED_ENTRY_FEE

        if check_member_fee:
            status = status and event.member_entry_fee == EXPECTED_MEMBER_ENTRY_FEE

        manager.save_results(
            status=status,
            test_name=f"Edit event and check fees - {player_format}- {test_name}",
            test_description="Edit an event, through the UI. Check the entry fees do not get corrupted.",
            output=f"{check_member_fee=} {EXPECTED_ENTRY_FEE=} {event.entry_fee=} {EXPECTED_MEMBER_ENTRY_FEE=} {event.member_entry_fee=}",
        )


class MemberFees:
    """Test scenarios for having member specific fees on an event

    In particular test for problems when an event is edited - causing entry fees to be multiplied COB-879

    """

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        mark = User.objects.filter(username="Mark").first()
        self.manager.login_user(mark)

        # Set up Congress
        org = Organisation.objects.filter(name="Fantasy Bridge Club").first()
        self.congress = test_create_congress("Entry Fee Congress", org)
        self.congress.save()

        # Set up event
        self.event = test_create_event("Team", self.congress)
        self.event.player_format = "Teams"
        self.event.entry_fee = EXPECTED_ENTRY_FEE
        self.event.save()

    def a1_update_event(self):
        """
        make a change to an event through the event form and see what happens
        """

        # Normal congress
        _change_data_and_check(
            self.congress,
            self.event,
            self.manager,
            "Normal Congress",
            check_member_fee=False,
        )

        # member rates
        self.congress.allow_member_entry_fee = True
        self.congress.save()
        _change_data_and_check(self.congress, self.event, self.manager, "Member fees")

        # member only
        self.congress.members_only = True
        self.congress.save()
        _change_data_and_check(self.congress, self.event, self.manager, "Member Only")

    def zz_clean_up(self):
        self.event.delete()
        self.congress.delete()
