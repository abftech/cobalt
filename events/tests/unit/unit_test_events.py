from datetime import timedelta
from decimal import Decimal

from django.utils.timezone import localdate, localtime

from accounts.models import User
from events.models import CongressMaster, Congress, Event, Session, EventPlayerDiscount
from organisations.models import Organisation
from tests.test_manager import CobaltTestManagerIntegration

ENTRY_FEE = 100.0
EARLY_DISCOUNT = 20


class EventsTests:
    """Unit tests for things related to Events"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager

    def events_model_functions(self):
        """Tests for functions that are part of the Event model"""

        # Create a congress
        org = Organisation.objects.get(pk=6)
        congress_master = CongressMaster(org=org, name="Model Test Congress Master")
        congress_master.save()
        congress = Congress(congress_master=congress_master)
        congress.save()

        self.manager.save_results(
            status=bool(congress),
            test_name="Create congress",
            test_description="Create a congress and check it works",
            output=f"Created a congress. Status={bool(congress)}",
        )

        # Create basic event
        event = Event(
            congress=congress,
            event_name="pytest event",
            event_type="Open",
            entry_fee=Decimal(ENTRY_FEE),
            entry_early_payment_discount=Decimal(EARLY_DISCOUNT),
            player_format="Pairs",
        )
        event.save()

        self.manager.save_results(
            status=bool(event),
            test_name="Create event",
            test_description="Create an event and check it works",
            output=f"Created an event. Status={bool(congress)}",
        )

        # Create session
        session = Session(event=event)

        self.manager.save_results(
            status=bool(session),
            test_name="Create session",
            test_description="Create a session within the event and check it works",
            output=f"Created a session. Status={bool(congress)}",
        )

        ####################################
        # Date checks                      #
        ####################################

        # With no dates, event should be open - pass
        self.manager.save_results(
            status=bool(event.is_open()),
            test_name="Event is open. No dates set.",
            test_description="Check that the event is open. We have not set any dates so it should be open by default.",
            output=f"Checked event open. Status={bool(event.is_open())}",
        )

        today = localdate()
        # time_now = localtime().time()

        # Set Open date to yesterday - pass
        event.entry_open_date = today - timedelta(days=1)

        self.manager.save_results(
            status=bool(event.is_open()),
            test_name="Event is open. Open date in past.",
            test_description="Add an open date in the past. Check that the event is open.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. Open date: {event.entry_open_date}",
        )

        # Set Open date to tomorrow - fail
        event.entry_open_date = today + timedelta(days=1)

        self.manager.save_results(
            status=not bool(event.is_open()),
            test_name="Event is not open. Open date in future.",
            test_description="Add an open date in the future. Check that the event is closed.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. Open date: {event.entry_open_date}",
        )

        # Set open date to yesterday so we we can test the close date
        event.entry_open_date = today - timedelta(days=1)

        # Add close date set to tomorrow - pass
        event.entry_close_date = today + timedelta(days=1)

        self.manager.save_results(
            status=bool(event.is_open()),
            test_name="Event is open. Open date in past. Close date in future.",
            test_description="Add a close date in the future. Check that the event is open.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}",
        )

        # Set close date to yesterday - fail
        event.entry_close_date = today - timedelta(days=1)

        self.manager.save_results(
            status=not bool(event.is_open()),
            test_name="Event is closed. Open date in past. Close date in past.",
            test_description="Add a close date in the past. Check that the event is closed.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}",
        )

        # Set close date to today and close time to future - pass
        event.entry_close_date = today
        event.entry_close_time = (localtime() + timedelta(hours=1)).time()

        self.manager.save_results(
            status=bool(event.is_open()),
            test_name="Event is open. Open date in past. Close date is today. Close time in future.",
            test_description="Add a close time in the future. Check that the event is open.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}. "
            f"Close date: {event.entry_close_time}",
        )

        # Set close date to today and close time to past - fail
        event.entry_close_time = (localtime() - timedelta(hours=1)).time()

        self.manager.save_results(
            status=not bool(event.is_open()),
            test_name="Event is closed. Open date in past. Close date is today. Close time in past.",
            test_description="Add a close time in the past. Check that the event is closed.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. Time: {localtime().time()} "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}. "
            f"Close date: {event.entry_close_time}",
        )

        # Set close date to today and close time to past (try 1 second) - fail
        event.entry_close_time = (localtime() - timedelta(seconds=1)).time()
        self.manager.save_results(
            status=not bool(event.is_open()),
            test_name="Event is closed. Open date in past. Close date is today. Close time in past by 1 second.",
            test_description="Add a close time in the past (by 1 second). Check that the event is closed.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. Time: {localtime().time()} "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}. "
            f"Close date: {event.entry_close_time}",
        )

        # Open event again so we can test the start date
        event.entry_close_date = today + timedelta(days=1)

        # Set start date in future - pass
        session.session_date = today + timedelta(days=7)
        session.session_start = (localtime() - timedelta(hours=1)).time()
        session.save()

        self.manager.save_results(
            status=bool(event.is_open()),
            test_name="Event is open. Open date in past. Close date is today. session date in future.",
            test_description="The event entry dates are fine (event is open) and the session date is in the future.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. Time: {localtime().time()} "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}. "
            f"Close date: {event.entry_close_time}. Session date: {session.session_date}. "
            f"Session start: {session.session_start}",
        )

        # Set start date in past - fail
        session.session_date = today - timedelta(days=7)
        session.save()

        self.manager.save_results(
            status=not bool(event.is_open()),
            test_name="Event is closed. Open date in past. Close date is today. session date in past.",
            test_description="The event entry dates are fine (event is open) and the session date is in the past.",
            output=f"Checked event open. Status={bool(event.is_open())}. Today: {today}. Time: {localtime().time()} "
            f"Open date: {event.entry_open_date}. Close date: {event.entry_close_date}. "
            f"Close date: {event.entry_close_time}. Session date: {session.session_date}. "
            f"Session start: {session.session_start}",
        )

        ##################
        # Entry Fees     #
        ##################

        # No discount
        player = User(
            first_name="Ready",
            last_name="PlayerOne",
            system_number=98989898,
            email="a@b.com",
        )
        player.save()
        fee, *_ = event.entry_fee_for(player)

        ok = fee == ENTRY_FEE / 2

        self.manager.save_results(
            status=ok,
            test_name="Event entry fee. Pairs. No discounts.",
            test_description="Check the entry fee for a player in a pairs event with no discounts is "
            "half the total entry fee.",
            output=f"Checked event entry fee for {player}. Expected {ENTRY_FEE / 2}. Got {fee}.",
        )

        # Early entry discount
        congress.allow_early_payment_discount = True
        congress.early_payment_discount_date = today + timedelta(days=1)
        congress.save()
        fee, _, desc, *_ = event.entry_fee_for(player)

        if fee == (ENTRY_FEE - EARLY_DISCOUNT) / 2 and desc == "Early discount":
            ok = True
        else:
            ok = False

        self.manager.save_results(
            status=ok,
            test_name="Event entry fee. Pairs. Early entry discount.",
            test_description="Check the entry fee for a player in a pairs event with early entry discount is "
            "half the total entry fee after deducting the discount.",
            output=f"Checked event entry fee for {player}. Expected {(ENTRY_FEE - EARLY_DISCOUNT)/ 2}. "
            f"Got {fee}. Expected description to be 'Early discount'. Got '{desc}'.",
        )

        # Youth Discount and early entry
        congress.allow_youth_payment_discount = True
        congress.youth_payment_discount_date = today
        congress.youth_payment_discount_age = 25
        congress.save()

        event.entry_youth_payment_discount = 50
        event.save()

        player.dob = today - timedelta(weeks=400)
        player.save()

        fee, _, desc, *_ = event.entry_fee_for(player)
        assert fee == ((ENTRY_FEE - EARLY_DISCOUNT) / 2) * (50 / 100)
        assert desc == "Youth+Early discount"

        # Remove Early discount
        congress.allow_early_payment_discount = False
        congress.save()

        fee, _, desc, *_ = event.entry_fee_for(player)
        assert fee == (ENTRY_FEE / 2) * (50 / 100)
        assert desc == "Youth discount"

        # Specific player discounts
        event_player_discount = EventPlayerDiscount(
            player=player, admin=player, event=event, entry_fee=4.55, reason="ABC"
        )
        event_player_discount.save()

        fee, _, desc, *_ = event.entry_fee_for(player)
        assert fee == 4.55
        assert desc == "ABC"
