import logging
from datetime import datetime, timedelta, date

import pytz
from django.db.models import Q, F
from django.template import loader
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone

import payments.views.core as payments_core  # circular dependency
from accounts.models import User

from cobalt.settings import (
    BRIDGE_CREDITS,
    TIME_ZONE,
    TBA_PLAYER,
    GLOBAL_CURRENCY_SYMBOL,
    AUTO_TOP_UP_LOW_LIMIT,
)

from logs.views import log_event
from notifications.models import BlockNotification, BatchID
from notifications.views.core import (
    send_cobalt_email_with_template,
    create_rbac_batch_id,
)
from payments.views.payments_api import (
    payment_api_batch,
    calculate_auto_topup_amount,
)
from rbac.core import rbac_get_users_with_role
from events.models import (
    BasketItem,
    EventEntry,
    EventEntryPlayer,
    PlayerBatchId,
    EventLog,
    Congress,
    Event,
    Session,
)

TZ = pytz.timezone(TIME_ZONE)

logger = logging.getLogger("cobalt")


def events_payments_secondary_callback(status, route_payload):
    """This gets called when (potentially) multiple payments have been made for an event_entry by
    someone other than the primary entrant.

    This is called when a user hits Pay All on the edit screen or when they click to pay only one players entry

    The only difference is number of items in the list of entries with matching batch ids

    """

    payment_user = _get_player_who_is_paying(status, route_payload)

    if not payment_user:
        return

    # Get players and entries that have been paid for (could be an empty list, but shouldn't be)
    paid_event_entry_players = _get_event_entry_players_from_payload(route_payload)

    if not paid_event_entry_players:
        return

    # Update entries
    for paid_event_entry_player in paid_event_entry_players:
        _mark_event_entry_player_as_paid_and_book_payments(
            paid_event_entry_player, payment_user
        )

    # Check if still in primary entrants basket and handle
    _events_payments_secondary_callback_process_basket(
        event_entry=paid_event_entry_players[0].event_entry,
        already_handled_event_entry_players=paid_event_entry_players,
        team_mate_who_triggered=payment_user,
    )

    # Check status of entry now
    for paid_event_entry_player in paid_event_entry_players:
        paid_event_entry_player.event_entry.check_if_paid()

    # Check for low balance
    _low_balance_check(payment_user)


def _events_payments_secondary_callback_process_basket(
    event_entry, already_handled_event_entry_players, team_mate_who_triggered
):
    """Handle this event still being in the primary users basket when a team mate makes a payment"""

    # This entry could have been in the primary players basket
    basket_item = BasketItem.objects.filter(event_entry=event_entry).first()

    if not basket_item:
        return

    # Delete from primary entrants basket if it was still there
    basket_item.delete()

    # Get the primary entrant, we now need to look at things from their point of view as if they had
    # checked out the entry
    primary_entrant = event_entry.primary_entrant

    # We should try to make any payments for this entry that would have been made if the primary entrant had
    # checked out, but only if we can do it without manual payment. And also send the emails.
    # We probably shouldn't do any team mate allowed payments as this user may not have access

    # TODO: NOT SURE WHAT TO DO WITH THIS. FOR NOW, DON'T PROCESS ANYTHING

    # # get all event_entry_players for this entry
    # event_entry_all_players = EventEntryPlayer.objects.filter(event_entry=event_entry)
    #
    # for event_entry_all_player in event_entry_all_players:
    #
    #     # Skip any that have already been handled
    #     if event_entry_all_player in already_handled_event_entry_players:
    #         continue
    #
    #     # From the point of view of the primary entrant
    #     if (
    #         # primary entrant said they would pay
    #         event_entry_all_player.payment_type == "my-system-dollars"
    #         # entry isn't yet paid
    #         and event_entry_all_player.payment_status not in ["Paid", "Free"]
    #         # payment works
    #         and payment_api_batch(
    #             member=primary_entrant,
    #             description=event_entry.event.event_name,
    #             amount=event_entry_all_player.entry_fee
    #             - event_entry_all_player.payment_received,
    #             organisation=event_entry.event.congress.congress_master.org,
    #             payment_type="Entry to an event",
    #             book_internals=False,
    #         )
    #     ):
    #         _mark_event_entry_player_as_paid_and_book_payments(
    #             event_entry_all_player, primary_entrant
    #         )

    # Check if status has changed
    event_entry.check_if_paid()

    # Let people know
    _send_notifications(
        # event_entry_players=event_entry_all_players,
        event_entry_players=already_handled_event_entry_players,
        event_entries=[event_entry],
        payment_user=primary_entrant,
        triggered_by_team_mate_payment=True,
        team_mate_who_triggered=team_mate_who_triggered,
    )


def events_payments_primary_callback(status, route_payload):
    """This gets called when a payment has been made for us.

    We supply the route_payload when we ask for the payment to be made and
    use it to update the status of payments.

    This gets called when the primary user who is entering the congress
    has made a payment.

    We can use the route_payload to find the payment_user (who entered and paid)
    as well as to find all of the EventEntryPlayer records that have been paid for if this was successful.

    We also need to notify everyone who has been entered which will include people who were not
    paid for by this payment. For that we use the basket of the primary user, which we then empty.

    This requires an EventEntry, a group of EventEntryPlayers with the route_payload attached,
    A PlayerBatchId to find the player who made this entry, and the BasketItems for that player.

    """

    payment_user = _get_player_who_is_paying(status, route_payload)

    if not payment_user:
        return

    # Get players and entries that have been paid for
    paid_event_entry_players = _get_event_entry_players_from_payload(route_payload)
    paid_event_entries = _get_event_entries_for_event_entry_players(
        paid_event_entry_players
    )

    # Update them
    _update_entries(
        paid_event_entry_players, paid_event_entries, payment_user, route_payload
    )

    # Get all players that are included in this bunch of entries
    notify_event_entry_players = _get_event_entry_players_from_basket(payment_user)
    notify_event_entries = _get_event_entries_for_event_entry_players(
        notify_event_entry_players
    )

    # Notify them
    _send_notifications(notify_event_entry_players, notify_event_entries, payment_user)

    # Tidy up
    _clean_up(notify_event_entries)

    # Check for low balance
    _low_balance_check(payment_user)


def _get_player_who_is_paying(status, route_payload):
    """Use the route_payload to find the player who is paying for this batch of entries
    Also checks the status (to avoid duplicate code) and deletes the PlayerBatchId object
    """

    if status != "Success":
        logger.warning(
            f"Received callback with status {status}. Payload {route_payload}. Ignoring."
        )
        return False

    # Find who is making this payment
    player_batch_id = PlayerBatchId.objects.filter(batch_id=route_payload).first()

    # catch error
    if not player_batch_id:
        log_event(
            user="Unknown",
            severity="CRITICAL",
            source="Events",
            sub_source="events_payments_callback",
            message=f"No matching player for route_payload: {route_payload}",
        )
        logger.critical(f"No matching player for route_payload: {route_payload}")
        return False

    payment_user = player_batch_id.player
    player_batch_id.delete()

    return payment_user


def _get_event_entry_players_from_payload(route_payload):
    """Returns the entries that are associated with the route_payload. Route_payload is sent as a parameter
    to Stripe so we when a payment is made we can find the corresponding entries.

    Note: These are the evententry_player records that were paid for, not the total entries.
          There could be other entries in this that were paid for using a different method."""

    return EventEntryPlayer.objects.filter(batch_id=route_payload)


def _get_event_entry_players_from_basket(payment_user):
    """Get all of the EventEntryPlayer records that need to be notified. Use the primary players basket."""

    return EventEntryPlayer.objects.filter(
        event_entry__basketitem__player=payment_user
    ).exclude(event_entry__entry_status="Cancelled")


def _get_event_entries_for_event_entry_players(event_entry_players):
    """Takes a list of event entry players and returns the parent event entries

    Args:
        event_entry_players: a query set of EventEntryPlayers

    Returns:
        event_entries: a query set of EventEntries
    """

    # Get all EventEntries for changed EventEntryPlayers
    event_entry_list = (
        event_entry_players.order_by("event_entry", "-id")
        .distinct("event_entry")
        .values_list("event_entry")
    )

    return EventEntry.objects.filter(pk__in=event_entry_list).exclude(
        entry_status="Cancelled"
    )


def _update_entries(event_entry_players, event_entries, payment_user, route_payload):
    """Update the database to reflect changes and make payments for
    other members if we have access."""

    # Change the entries that have been paid for
    _update_entries_change_entries(event_entry_players, payment_user)

    # Check if we can now pay using "their system dollars"
    _update_entries_process_their_system_dollars(payment_user)

    # Update status
    for event_entry in event_entries:
        event_entry.check_if_paid()


def _update_entries_change_entries(event_entry_players, payment_user):
    """First part of _update_entries. This changes the entries themselves"""

    # Update EntryEventPlayer objects
    for event_entry_player in event_entry_players:
        _mark_event_entry_player_as_paid_and_book_payments(
            event_entry_player, payment_user
        )


def _mark_event_entry_player_as_paid_and_book_payments(event_entry_player, who_paid):
    """Update a single event_entry_player record to be paid, and create the payments for the
    user and the organisation"""

    # this could be a partial payment
    amount = event_entry_player.entry_fee - event_entry_player.payment_received

    event_entry_player.payment_status = "Paid"
    event_entry_player.payment_received = event_entry_player.entry_fee
    event_entry_player.paid_by = who_paid
    event_entry_player.entry_complete_date = timezone.now().astimezone(TZ)
    event_entry_player.save()

    EventLog(
        event=event_entry_player.event_entry.event,
        actor=event_entry_player.paid_by,
        action=f"Paid for {event_entry_player.player} with {amount} {BRIDGE_CREDITS}",
        event_entry=event_entry_player.event_entry,
    ).save()

    log_event(
        user=event_entry_player.paid_by,
        severity="INFO",
        source="Events",
        sub_source="events_entry",
        message=f"{event_entry_player.paid_by.href} paid for {event_entry_player.player.href} to enter {event_entry_player.event_entry.event.href}",
    )

    # create payments in org account
    payments_core.update_organisation(
        organisation=event_entry_player.event_entry.event.congress.congress_master.org,
        amount=amount,
        description=f"{event_entry_player.event_entry.event.event_name} - {event_entry_player.player}",
        payment_type="Entry to an event",
        member=who_paid,
        event=event_entry_player.event_entry.event,
    )

    # create payment for user
    payments_core.update_account(
        member=who_paid,
        amount=-amount,
        description=f"{event_entry_player.event_entry.event.event_name} - {event_entry_player.player}",
        payment_type="Entry to an event",
        organisation=event_entry_player.event_entry.event.congress.congress_master.org,
    )


def _update_entries_process_their_system_dollars(payment_user):
    # sourcery skip: extract-method
    """Now process their system dollar transactions (if any)
    We want to batch these up by player and congress so we don't do excessive auto top ups.

    We need to get the list of possible entries to check, which may not be entries that had a payment made as
    part of the primary entrant checking out. For example, if the primary entrant chooses to pay cash, but uses
    their-system-dollars for their partner, then we won't find their partner's entry by looking at the
    entries with payments (there aren't any). In fact the callback is no use at all at finding them based upon the
    route_payload. The only thing we can do is to use the payment_user (who entered) and look in their basket.
    (Obviously, we are using the route_payload to find the payment_user, so it is still useful.)

    What if someone puts two entries in with cash and their partner paying using their-system-dollars and then
    only checks out one of those entries? The second entry (in the basket) will also process their partners
    my-system-dollars payment. However, it is not actually possible to do this. You can checkout all entries in
    your basket or you can click pay now on one entry which will pay with bridge credits, not the entered payment
    method.

    """

    # build a dictionary with players
    (
        event_entries,
        event_entries_by_player,
    ) = _update_entries_process_their_system_dollars_build_dict(payment_user)

    # Now go through each player and do auto top up for full amount if required
    _update_entries_process_their_system_dollars_make_payments(event_entries_by_player)


def _update_entries_process_their_system_dollars_build_dict(payment_user):
    """Sub process for handling their system dollars. This builds the dictionary of players"""

    event_entries_as_dict = BasketItem.objects.filter(player=payment_user).values(
        "event_entry"
    )

    # Start by building a dictionary with player then list of event_entry_players to pay for
    event_entries_by_player = {}
    event_entries = []

    for event_entry_id in event_entries_as_dict:
        event_entry = EventEntry.objects.get(pk=event_entry_id["event_entry"])
        event_entries.append(event_entry)

        for event_entry_player in event_entry.evententryplayer_set.all():
            if (
                event_entry_player.payment_type == "their-system-dollars"
                and event_entry_player.payment_status not in ["Paid", "Free"]
            ):
                this_player = event_entry_player.player

                # Add key if not present
                if this_player not in event_entries_by_player:
                    event_entries_by_player[this_player] = []

                # Add event_entry_player to list
                event_entries_by_player[this_player].append(event_entry_player)

    return event_entries, event_entries_by_player


def _update_entries_process_their_system_dollars_make_payments(event_entries_by_player):
    """Sub process for handling their system dollars - make payments"""

    for this_player in event_entries_by_player:
        total_amount_for_player = 0.0
        for event_entry_player in event_entries_by_player[this_player]:
            total_amount_for_player += float(event_entry_player.entry_fee) - float(
                event_entry_player.payment_received
            )

        # we now have the players total for all events in all congresses. See if this is enough.
        player_balance = payments_core.get_balance(this_player)

        if total_amount_for_player > player_balance:

            # Top up required
            topup_amount = calculate_auto_topup_amount(
                this_player, total_amount_for_player, player_balance
            )
            status, msg = payments_core.auto_topup_member(this_player, topup_amount)

            if not status:
                # Payment failed - abandon for this user. the called functions will handle notifying them
                logger.error(f"Auto top up for {this_player} failed: {msg}")
                continue

        # Now go through and make all of the payments, they should work as there is enough money
        for event_entry_player in event_entries_by_player[this_player]:

            event_entry = event_entry_player.event_entry

            if payment_api_batch(
                member=event_entry_player.player,
                description=event_entry.event.event_name,
                amount=event_entry_player.entry_fee,
                organisation=event_entry_player.event_entry.event.congress.congress_master.org,
                payment_type="Entry to an event",
                book_internals=True,
                event=event_entry.event,
            ):
                event_entry_player.payment_status = "Paid"
                event_entry_player.entry_complete_date = datetime.now()
                event_entry_player.paid_by = event_entry_player.player
                event_entry_player.payment_received = event_entry_player.entry_fee
                event_entry_player.save()

                EventLog(
                    event=event_entry.event,
                    actor=event_entry_player.player,
                    action=f"Paid with {BRIDGE_CREDITS}",
                    event_entry=event_entry,
                ).save()

                logger.info(
                    f"{event_entry_player.player} paid with their-system-dollars for {event_entry}"
                )
            else:
                logger.warning(
                    f"{event_entry_player.player} payment failed for their-system-dollars for {event_entry}"
                )


def _send_notifications(
    event_entry_players,
    event_entries,
    payment_user,
    triggered_by_team_mate_payment=False,
    team_mate_who_triggered=None,
):
    """Send the notification emails for a particular set of events that has just been paid for

    Args:
        event_entry_players: queryset of EventEntryPlayer. This is a list of people who have
                             just been entered in events and need to be informed
        event_entries: list of event entries that fit with this payment
        payment_user: User. The person who paid
        triggered_by_team_mate_payment: whether this set of notifications was caused by someone other than the
                            primary entrant making a payment (was in the primary entrants basket)

    """

    # First we want to structure our data to be player.congress.event.event_entry_player
    # This gives us the player (who we will send an email to), any congress they are in,
    # any event they are in (in a congress) and who else is in that entry
    struct = _send_notifications_build_struct(event_entry_players)

    # Loop through by player, then congress and send email. 1 email per player per congress
    for player, value in struct.items():
        for congress in value:
            send_email_to_player_entered_into_event_by_another(
                player=player,
                congress=congress,
                event_entry_players=event_entry_players,
                struct=struct,
                event_entries=event_entries,
                payment_user=payment_user,
                triggered_by_team_mate_payment=triggered_by_team_mate_payment,
                team_mate_who_triggered=team_mate_who_triggered,
            )

    # Notify conveners as well
    _send_notifications_notify_conveners(event_entries)


def send_email_to_player_entered_into_event_by_another(
    player,
    congress,
    event_entry_players,
    struct,
    event_entries,
    payment_user,
    triggered_by_team_mate_payment,
    team_mate_who_triggered,
):
    """sends an email to someone who has been entered in an event by someone else"""

    # What payment types are we expecting?
    payment_types = list(
        event_entry_players.filter(event_entry__event__congress=congress)
        .values_list("payment_type", flat=True)
        .distinct()
    )

    # Has this user paid?
    user_owes_money = (
        event_entry_players.filter(player=player)
        .filter(event_entry__event__congress=congress)
        .exclude(payment_status="Paid")
        .exclude(payment_status="Free")
        .exclude(event_entry__entry_status="Cancelled")
        .exists()
    )

    # Use the template to build the email for this user and this congress
    html = loader.render_to_string(
        "events/players/email/player_event_entry.html",
        {
            "player": player,
            "events_struct": struct[player][congress],
            "payment_user": payment_user,
            "congress": congress,
            "event": event_entries,
            "payment_types": payment_types,
            "user_owes_money": user_owes_money,
            "triggered_by_team_mate_payment": triggered_by_team_mate_payment,
            "team_mate_who_triggered": team_mate_who_triggered,
        },
    )

    context = {
        "name": player.first_name,
        "title": f"Event Entry - {congress}",
        "email_body": html,
        "link": "/events/view",
        "link_text": "View Entry",
        "subject": f"Event Entry - {congress}",
    }

    # create batch ID
    batch_id = create_rbac_batch_id(
        rbac_role=f"events.org.{congress.congress_master.org.id}.edit",
        organisation=congress.congress_master.org,
        batch_type=BatchID.BATCH_TYPE_ENTRY,
        description=f"Event entry - {congress}",
        batch_size=1,
        complete=True,
    )

    logger.info(f"Sending email to {player}")
    send_cobalt_email_with_template(
        to_address=player.email,
        context=context,
        batch_id=batch_id,
        apply_default_template_for_club=congress.congress_master.org,
    )


def _send_notifications_build_struct(event_entry_players):
    """sub function to build the structure to use for emails"""

    struct = {}

    # Create structure
    for event_entry_player in event_entry_players:
        player = event_entry_player.player
        event = event_entry_player.event_entry.event
        congress = event.congress

        # Skip TBA
        if player.id == TBA_PLAYER:
            continue

        # Add if not present struct[player]
        if player not in struct:
            struct[player] = {}

        # Add if not present struct[player][congress] only if player is in this congress
        if congress not in struct[player] and event_entry_players.filter(
            player=player
        ).filter(event_entry__event__congress=congress):
            struct[player][congress] = {}

        # Add if not present struct[player][congress][event] only if player is in this event
        if event not in struct[player][congress] and event_entry_players.filter(
            player=player
        ).filter(event_entry__event=event):
            struct[player][congress][event] = []

    # Populate structure
    for event_entry_player in event_entry_players:
        player = event_entry_player.player
        event = event_entry_player.event_entry.event
        congress = event.congress

        for this_player in struct:
            # Add players if we can
            try:
                struct[this_player][congress][event].append(event_entry_player)
            except KeyError:
                # No place to put this, so we don't need it
                pass

    return struct


def _send_notifications_notify_conveners(event_entries):
    """Notify conveners about an entry coming in"""

    # Notify conveners

    for event_entry in event_entries:
        players = EventEntryPlayer.objects.filter(event_entry=event_entry).order_by(
            "pk"
        )

        html = loader.render_to_string(
            "events/players/email/notify_convener_about_event_entry.html",
            {
                "event_entry": event_entry,
                "players": players,
            },
        )

        event = event_entry.event
        congress = event.congress

        # create batch ID
        batch_id = create_rbac_batch_id(
            rbac_role=f"events.org.{congress.congress_master.org.id}.edit",
            organisation=congress.congress_master.org,
            batch_type=BatchID.BATCH_TYPE_ENTRY,
            description=f"New Entry to {event.event_name} in {congress}",
            complete=True,
        )

        batch_size = notify_conveners(
            congress,
            event,
            f"New Entry to {event.event_name} in {congress}",
            html,
            batch_id=batch_id,
        )

        # update the batch_id
        batch_id.batch_size = batch_size
        batch_id.state = BatchID.BATCH_STATE_COMPLETE
        batch_id.save()


def _clean_up(notify_event_entries):
    """delete any leftover basket items. If we are notifying a user about this, then it should be removed."""

    BasketItem.objects.filter(
        event_entry__in=notify_event_entries.values_list("id")
    ).delete()

    # Check status as basket item is now an option
    for event_entry in notify_event_entries:
        event_entry.check_if_paid()


def get_basket_for_user(user):
    """called by base html to show basket"""
    return BasketItem.objects.filter(player=user).count()


def _get_events_event_entry_players(user):
    """sub of get_events to handle the main things to do with event_entry_players"""

    # Main query
    event_entry_players_query = (
        EventEntryPlayer.objects.filter(player=user)
        .exclude(event_entry__entry_status="Cancelled")
        .exclude(event_entry__event__denormalised_end_date__lt=datetime.today())
        .order_by("event_entry__event__denormalised_start_date")
        .select_related("event_entry__event")
    )

    # total number of events this user has coming up
    total_events = event_entry_players_query.count()

    # get last 6
    event_entry_players = event_entry_players_query[:6]

    # We get 6 but show 5. If we have 6 then show the more button
    more_events = len(event_entry_players) == 6

    # Drop the 6th if we have one
    event_entry_players = event_entry_players[:5]

    return event_entry_players, more_events, total_events


def _get_events_basket_items(event_entry_players, user):
    """sub of get_events to handle loading the basket items efficiently"""

    # Load basket items in one hit
    event_entry_list = [
        event_entry_player.event_entry for event_entry_player in event_entry_players
    ]
    basket_items = BasketItem.objects.filter(
        event_entry__in=event_entry_list
    ).select_related("event_entry")

    # Create dicts
    users_basket = []
    other_basket = {}

    for basket_item in basket_items:
        if basket_item.player == user:
            users_basket.append(basket_item.event_entry)
        else:
            other_basket[basket_item.event_entry] = basket_item.player

    return users_basket, other_basket


def _get_event_start_date_from_sessions(event_entry_players):
    """
    Sub of get_event to calculate the effective start date for an event based upon today's date.

    Most events run for one or more continuous days, but events with a break in them, e.g. every Monday for
    a month, we want to set the event start date to be the next session, not the first session.

    """

    # load all sessions in one hit
    events_list = [
        event_entry_player.event_entry.event
        for event_entry_player in event_entry_players
    ]
    sessions = (
        Session.objects.filter(event__in=events_list)
        .order_by("event", "session_date")
        .select_related("event")
    )

    today = timezone.localdate()

    event_start_dates = {}
    for session in sessions:
        # See if this is the next or current session for this event
        if session.event not in event_start_dates:
            # No session yet, so we win by default
            event_start_dates[session.event] = session.session_date

        # For example. today=9. ses1=5, ses2=12, ses3=19
        # We are checking ses3 and 12 is the current winner (ses2). It should stay the current winner.
        # ses_date > existing - TICK
        # ses_date >= today - TICK
        # today > existing - CROSS
        elif (
            session.session_date > event_start_dates[session.event]
            and session.session_date >= today
            and today > event_start_dates[session.event]
        ):
            event_start_dates[session.event] = session.session_date

    return event_start_dates


def get_events(user):
    """called by dashboard to get upcoming events"""

    # Load event_entry_players for this user
    event_entry_players, more_events, total_events = _get_events_event_entry_players(
        user
    )

    # Flag for unpaid entries. Default to False.
    unpaid = False

    # set up basket items lists/dictionaries
    users_basket, other_basket = _get_events_basket_items(event_entry_players, user)

    event_start_dates = _get_event_start_date_from_sessions(event_entry_players)

    # Augment data
    for event_entry_player in event_entry_players:
        # Set start date based upon sessions

        event_entry_player.calculated_start_date = event_start_dates[
            event_entry_player.event_entry.event
        ]

        if event_entry_player.calculated_start_date == timezone.localdate():
            event_entry_player.is_running = True

        # Check if still in cart
        event_entry_player.in_cart = event_entry_player.event_entry in users_basket

        # Check if still in someone else's cart (we want to know whose as well)
        if event_entry_player.event_entry in other_basket:
            event_entry_player.in_other_cart = other_basket[
                event_entry_player.event_entry
            ]
            # we do not want to show other player's cart item as unpaid item, in fact
            # we do not want to show them to the player at all
            continue

        # check if unpaid
        if event_entry_player.payment_status == "Unpaid":
            unpaid = True

    return event_entry_players, unpaid, more_events, total_events


def get_conveners_for_congress(congress):
    """get list of conveners for a congress"""

    role = f"events.org.{congress.congress_master.org.id}.edit"
    return rbac_get_users_with_role(role)


def convener_wishes_to_be_notified(congress, convener):
    """Checks with blocked notifications in Notifications to see if this convener wants to know about events that
    happen or not. Currently it is binary (Yes, or No), later it could be extended to check for specific actions"""

    # Get any blocks in place for notifications

    # We want rows for this user, and then either identifier is by Event and model_id is event.id OR
    # identifier is by Org and model_id is org.id

    return not BlockNotification.objects.filter(member=convener).filter(
        (
            (Q(model_id=congress.congress_master.id) | Q(model_id=None))
            & Q(identifier=BlockNotification.Identifier.CONVENER_EMAIL_BY_EVENT)
        )
        | (
            (Q(model_id=congress.congress_master.org.id) | Q(model_id=None))
            & Q(identifier=BlockNotification.Identifier.CONVENER_EMAIL_BY_ORG)
        )
    )


def notify_conveners(congress, event, subject, email_msg, batch_id=None):
    """Let conveners know about things that change.

    Returns a count of the emails sent"""

    sent_count = 0

    congress_contact_already_emailed = False
    conveners = get_conveners_for_congress(congress)
    link = reverse("events:admin_event_summary", kwargs={"event_id": event.id})

    for convener in conveners:

        # skip if this convener doesn't want the message
        if not convener_wishes_to_be_notified(congress, convener):
            continue

        context = {
            "name": convener.first_name,
            "title": "Convener Msg: " + subject,
            "subject": subject,
            "email_body": f"{email_msg}<br><br>",
            "link": link,
            "link_text": "View Event",
        }

        send_cobalt_email_with_template(
            to_address=convener.email,
            context=context,
            batch_id=batch_id,
            apply_default_template_for_club=congress.congress_master.org,
        )
        sent_count += 1

        if congress.contact_email and convener.email == congress.contact_email:
            congress_contact_already_emailed = True

    if congress.contact_email and not congress_contact_already_emailed:

        # send it to the congress contact email as well
        context = {
            "name": "Congress Contact",
            "title": "Convener Msg: " + subject,
            "subject": subject,
            "email_body": f"{email_msg}<br><br>",
            "link": link,
            "link_text": "View Event",
        }

        send_cobalt_email_with_template(
            to_address=congress.contact_email,
            context=context,
            batch_id=batch_id,
            apply_default_template_for_club=congress.congress_master.org,
        )
        sent_count += 1

    return sent_count


def events_status_summary():
    """Used by utils status to get the status of events"""

    #    now = datetime.now().date()
    now = timezone.now().date()
    last_day_date_time = timezone.now() - timedelta(hours=24)
    last_hour_date_time = timezone.now() - timedelta(hours=1)

    active_congresses = (
        Congress.objects.filter(status="Published")
        .filter(start_date__lte=now)
        .filter(end_date__gte=now)
        .count()
    )
    upcoming_congresses = (
        Congress.objects.filter(status="Published").filter(start_date__gt=now).count()
    )
    upcoming_entries = EventEntryPlayer.objects.filter(
        event_entry__event__congress__start_date__gt=now
    ).count()
    entries_last_24_hours = EventEntry.objects.filter(
        first_created_date__gt=last_day_date_time
    ).count()
    entries_last_hour = EventEntry.objects.filter(
        first_created_date__gt=last_hour_date_time
    ).count()

    return {
        "active": active_congresses,
        "upcoming": upcoming_congresses,
        "upcoming_entries": upcoming_entries,
        "entries_last_24_hours": entries_last_24_hours,
        "entries_last_hour": entries_last_hour,
    }


def sort_events_by_start_date(events):
    """Add the start date to a list of events and sort by start date"""

    # add start date and sort by start date
    events_list = {}
    for event in events:
        event.event_start_date = event.start_date()
        events_list[event] = event.event_start_date or date(year=1967, month=5, day=3)
    return {
        key: value
        for key, value in sorted(events_list.items(), key=lambda item: item[1])
    }


def get_event_statistics():
    """get stats about events, called by utils statistics"""

    users_have_played_in_congress = EventEntryPlayer.objects.distinct("player").count()
    total_congresses = Congress.objects.filter(status="Published").count()
    total_events = Event.objects.filter(congress__status="Published").count()
    total_sessions = Session.objects.count()
    total_player_entries = EventEntryPlayer.objects.count()

    return {
        "users_have_played_in_congress": users_have_played_in_congress,
        "total_congresses": total_congresses,
        "total_events": total_events,
        "total_sessions": total_sessions,
        "total_player_entries": total_player_entries,
    }


def get_completed_congresses_with_money_due(congress=None):
    """
    Find congresses which are finished but still have outstanding money to collect

    Optionally only list a single congress
    """

    event_entry_players_needing_attention = get_event_entry_players_needing_attention(
        congress
    )

    # filter
    congress_list = event_entry_players_needing_attention.values_list(
        "event_entry__event__congress"
    ).distinct("event_entry__event__congress")

    return Congress.objects.filter(pk__in=congress_list)


def get_event_entry_players_needing_attention(congress):
    """Get the entries that are causing a congress to be in an unfinished state"""

    # Get the player entries that are causing problems
    event_entry_players_needing_attention = (
        # Look at entries in congresses that have finished
        EventEntryPlayer.objects.filter(
            event_entry__event__congress__end_date__lt=timezone.now()
        )
        # ignore paid or free entries
        .exclude(payment_status__in=["Paid", "Free"])
        # Some edited entries are paid but marked as unpaid
        .exclude(entry_fee=F("payment_received"))
        # Ignore cancelled entries
        .exclude(event_entry__entry_status="Cancelled")
        # Ignore anything with no money due
        .exclude(entry_fee=0)
        # also get the event and congress - maybe later, see how it goes
        # .select_related("event_entry__event")
        .select_related("event_entry__event__congress")
    )

    # If we got a congress, then only show that one
    if congress:
        event_entry_players_needing_attention = (
            event_entry_players_needing_attention.filter(
                event_entry__event__congress=congress
            )
        )

    return event_entry_players_needing_attention


def fix_closed_congress(congress, actor):
    """sort out a congress that has finished with unpaid entries"""

    event_entry_players_needing_attention = get_event_entry_players_needing_attention(
        congress
    )

    if not event_entry_players_needing_attention:
        return "No errors found with congress. Nothing to do."

    event = event_entry_players_needing_attention[0].event_entry.event
    count = 0

    for event_entry_player in event_entry_players_needing_attention:
        # Change from unpaid bridge credits to unpaid non-bridge credits

        action = f"Fixed event entry player. Changed {event_entry_player.player}(Entry: {event_entry_player.id}) from '{event_entry_player.get_payment_type_display()}' to 'System Adjusted' and marked as paid. Previous amount paid was {GLOBAL_CURRENCY_SYMBOL}{event_entry_player.payment_received:.2f}"

        event_entry_player.payment_type = "System Adjusted"
        event_entry_player.payment_received = event_entry_player.entry_fee
        event_entry_player.payment_status = "Paid"
        event_entry_player.save()
        # log it
        logger.info(action)
        EventLog(
            event=event,
            actor=actor,
            event_entry=event_entry_player.event_entry,
            action=action,
        ).save()

        # Update event entry as well. This may be called multiple times but doesn't really matter
        event_entry_player.event_entry.entry_status = EventEntry.EntryStatus.COMPLETE
        event_entry_player.event_entry.save()

        count += 1

    return f"Congress fixed. {count} player{pluralize(count)} updated."


def _low_balance_check(member: User):
    """
    Check if a user has a low balance. For most things (book_internals=True) this is done by payments, but for
    events we book the member transactions ourselves, so we have to do this after payments has finished its part.

    For the special case of the balance being zero we do not send a warning. This will be the case if someone has
    paid only for this event or if they had exactly the right amount of money in their count for this entry. This
    is so likely to be deliberate that we do not annoy them with a warning.

    Args:
        member: User

    Returns: None

    """

    balance = payments_core.get_balance(member)

    if balance < AUTO_TOP_UP_LOW_LIMIT and balance != 0.0:
        payments_core.low_balance_warning(member)
