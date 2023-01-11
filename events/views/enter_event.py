from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from accounts.models import User, TeamMate
from cobalt.settings import TBA_PLAYER, BRIDGE_CREDITS
from events.models import (
    Session,
    Category,
    EventEntry,
    EventLog,
    BasketItem,
    EventEntryPlayer,
    Event,
    Congress,
    EVENT_PLAYER_FORMAT_SIZE,
)
from events.views.core import get_basket_for_user
from events.views.views import _checkout_perform_action
from utils.templatetags.cobalt_tags import cobalt_credits


def enter_event_non_post(event, congress, request, enter_for_another):
    """Handle a blank entry. Build the page and return to user."""

    # Start day and time of event
    event_start = (
        Session.objects.filter(event=event)
        .order_by("session_date", "session_start")
        .first()
    )

    # categories
    categories = Category.objects.filter(event=event)

    return render(
        request,
        "events/players/enter_event/enter_event.html",
        {
            "congress": congress,
            "event": event,
            "categories": categories,
            "event_start": event_start,
            "enter_for_another": enter_for_another,
        },
    )


def _get_team_mates_for_event(user, event):
    """Get available team mates for this event and this user"""

    # Get teammates for this user - exclude anyone entered already
    all_team_mates = TeamMate.objects.filter(user=user)
    team_mates_list = all_team_mates.values_list("team_mate")
    entered_team_mates = (
        EventEntryPlayer.objects.filter(event_entry__event=event)
        .exclude(event_entry__entry_status="Cancelled")
        .filter(player__in=team_mates_list)
        .values_list("player")
    )
    return all_team_mates.exclude(team_mate__in=entered_team_mates)


def _get_basic_data_from_request(request):
    """gets the data from the HTMX request and loads the common things that we need

    Called by enter_event_players_area_htmx
    """

    # Get HTMX parameters
    enter_for_another = request.POST.get("enter_for_another") == 1
    event_id = request.POST.get("event_id")
    # player0_id = request.POST.get("player0_id")

    # Load data
    event = get_object_or_404(Event.objects.select_related("congress"), pk=event_id)
    congress = event.congress
    # player0 = get_object_or_404(User, pk=player0_id)

    # get payment types for this congress
    pay_methods = congress.get_payment_methods()

    # Get available team mates
    team_mates = _get_team_mates_for_event(request.user, event)

    return event, congress, enter_for_another, pay_methods, team_mates


def _get_data_for_player0(
    congress, event, pay_methods, enter_for_another, name_list, this_user
):
    """sets up what we need for player0"""

    # set values for player0 (the user)
    entry_fee, discount, reason, description = event.entry_fee_for(this_user)

    payment_selected = pay_methods[0]
    entry_fee_pending = ""
    entry_fee_you = entry_fee

    # Player 0 settings depend upon whether this is the first entry or entering for someone else
    if enter_for_another:

        # Add ask them to pay as an option
        pay_methods_player0 = pay_methods.copy()
        if congress.payment_method_system_dollars:
            pay_methods_player0.append(("other-system-dollars", "Ask them to pay"))

        player0 = {
            "id": TBA_PLAYER,
            "payment_choices": pay_methods_player0,
            "payment_selected": payment_selected,
            "name": "TBA",
            "name_choices": name_list,
            "entry_fee_you": f"{entry_fee_you}",
            "entry_fee_pending": f"{entry_fee_pending}",
        }
    else:
        player0 = {
            "id": this_user.id,
            "payment_choices": pay_methods.copy(),
            "payment_selected": payment_selected,
            "name": this_user.full_name,
            "name_choices": name_list,
            "entry_fee_you": f"{entry_fee_you}",
            "entry_fee_pending": f"{entry_fee_pending}",
        }

    return player0, reason, discount, description


def _build_list_of_players_form(
    congress, event, request, pay_methods, team_mates, enter_for_another
):
    """
    sets up the data for this user (player0) and a list of other entry lines (player1..2..3 etc)
    """

    # build our form
    our_form = []

    # List of names for the dropdown
    name_list = [(0, "Search..."), (TBA_PLAYER, "TBA")]
    for team_mate in team_mates:
        item = team_mate.team_mate.id, f"{team_mate.team_mate.full_name}"
        name_list.append(item)

    # Get details of player0
    player0, reason, discount, description = _get_data_for_player0(
        congress, event, pay_methods, enter_for_another, name_list, request.user
    )

    # add another option for everyone except the current user
    if congress.payment_method_system_dollars:
        pay_methods.append(("other-system-dollars", "Ask them to pay"))

    # set values for other players
    team_size = EVENT_PLAYER_FORMAT_SIZE[event.player_format]
    min_entries = team_size
    if team_size == 6:
        min_entries = 4
    name_selected = None
    entry_fee = None

    for ref in range(1, team_size):

        payment_selected = pay_methods[0]
        # only ABF dollars go in the you column
        if payment_selected == "my-system-dollars":
            entry_fee_you = entry_fee
            entry_fee_pending = ""
        else:
            entry_fee_you = ""
            entry_fee_pending = entry_fee

        if payment_selected == "their-system-dollars":
            augment_payment_types = [
                ("their-system-dollars", f"Their {BRIDGE_CREDITS}")
            ]
        else:
            augment_payment_types = []

        item = {
            "player_no": ref,
            "payment_choices": pay_methods + augment_payment_types,
            "payment_selected": payment_selected,
            "name_choices": name_list,
            "name_selected": name_selected,
            "entry_fee_you": entry_fee_you,
            "entry_fee_pending": entry_fee_pending,
        }

        our_form.append(item)

    return player0, our_form, min_entries, reason, discount, description


def _get_alert_message_from_reason(reason, event, discount):
    """takes in the reason for a fee being as it is and produces a message for the user"""

    alert_msg = None

    if reason == "Early discount":
        date_field = event.congress.early_payment_discount_date.strftime("%d/%m/%Y")
        alert_msg = [
            "Early Entry Discount",
            f"You qualify for an early discount if you enter now. You will save {cobalt_credits(discount)} on this event. Discount valid until {date_field}.",
        ]

    if reason == "Youth discount":
        alert_msg = [
            "Youth Discount",
            f"You qualify for a youth discount for this event. A saving of {cobalt_credits(discount)}.",
        ]

    if reason == "Youth+Early discount":
        alert_msg = [
            "Youth and Early Discount",
            f"You qualify for a youth discount as well as an early entry discount for this event. A saving of {cobalt_credits(discount)}.",
        ]

    return alert_msg


@login_required()
def enter_event_players_area_htmx(request):
    """builds the entry part of the event entry page the first time we are loaded"""

    # Load basic info
    (
        event,
        congress,
        enter_for_another,
        pay_methods,
        team_mates,
    ) = _get_basic_data_from_request(request)

    # Get details for player0 and a list of other players as well as the minimum number of entries
    (
        player0,
        our_form,
        min_entries,
        reason,
        discount,
        description,
    ) = _build_list_of_players_form(
        congress, event, request, pay_methods, team_mates, enter_for_another
    )

    # use reason etc from above to see if discounts apply
    alert_msg = _get_alert_message_from_reason(reason, event, discount)

    return render(
        request,
        "events/players/enter_event/enter_event_players_area_htmx.html",
        {
            "enter_for_another": enter_for_another,
            "player0": player0,
            "alert_msg": alert_msg,
            "discount": discount,
            "description": description,
            "our_form": our_form,
        },
    )


def enter_event_post(request, congress, event):
    """Handle a post request to enter an event"""

    # create event_entry
    event_entry = EventEntry()
    event_entry.event = event
    event_entry.primary_entrant = request.user
    event_entry.comment = request.POST.get("comment", None)

    # see if we got a category
    category = request.POST.get("category", None)
    if category:
        event_entry.category = get_object_or_404(Category, pk=category)

    # see if we got a free format answer
    answer = request.POST.get("free_format_answer", None)
    if answer:
        event_entry.free_format_answer = answer[:60]

    # see if we got a team name
    team_name = request.POST.get("team_name", None)
    if team_name and team_name != "":
        event_entry.team_name = team_name

    event_entry.save()

    # Log it
    EventLog(
        event=event,
        actor=event_entry.primary_entrant,
        action=f"Event entry {event_entry.id} created",
        event_entry=event_entry,
    ).save()

    # add to basket
    basket_item = BasketItem()
    basket_item.player = request.user
    basket_item.event_entry = event_entry
    basket_item.save()

    # Get players from form
    #    players = {0: request.user}
    #    player_payments = {0: request.POST.get("player0_payment")}
    players = {}
    player_payments = {}

    for p_id in range(6):
        p_string = f"player{p_id}"
        ppay_string = f"player{p_id}_payment"
        if p_string in request.POST:
            p_string_value = request.POST.get(p_string)
            if p_string_value != "":
                players[p_id] = get_object_or_404(User, pk=int(p_string_value))
                player_payments[p_id] = request.POST.get(ppay_string)
            # regardless of what we get sent - 5th and 6th players are free
            if p_id > 3:
                player_payments[p_id] = "Free"

    # validate
    if (event.player_format == "Pairs" and len(players) != 2) or (
        event.player_format == "Teams" and len(players) < 4
    ):
        print("invalid number of entries")
        return

    # create player entries
    for p_id in range(len(players)):

        event_entry_player = EventEntryPlayer()
        event_entry_player.event_entry = event_entry
        event_entry_player.player = players[p_id]
        event_entry_player.payment_type = player_payments[p_id]
        entry_fee, discount, reason, description = event.entry_fee_for(
            event_entry_player.player
        )
        if p_id < 4:
            event_entry_player.entry_fee = entry_fee
            event_entry_player.reason = reason
        else:
            event_entry_player.entry_fee = 0
            event_entry_player.reason = "Team > 4"
            event_entry_player.payment_status = "Free"

        # set payment status depending on payment type
        if event_entry_player.payment_status not in [
            "Paid",
            "Free",
        ] and event_entry_player.payment_type in [
            "bank-transfer",
            "cash",
            "cheque",
        ]:
            event_entry_player.payment_status = "Pending Manual"
        event_entry_player.save()

        # Log it
        EventLog(
            event=event,
            actor=event_entry.primary_entrant,
            action=f"Event entry player {event_entry_player.id} created for {event_entry_player.player}",
            event_entry=event_entry,
        ).save()

    if "now" in request.POST:
        # if only one thing in basket, go straight to checkout
        if get_basket_for_user(request.user) == 1:
            return _checkout_perform_action(request)
        else:
            return redirect("events:checkout")

    else:  # add to cart and keep shopping
        msg = "Added to your cart"
        return redirect(f"/events/congress/view/{event.congress.id}?msg={msg}#program")


@login_required()
def enter_event(request, congress_id, event_id, enter_for_another=0):
    """enter an event

    Some people want to enter on behalf of their friends so we allow an extra parameter to handle this.

    """

    # Load the event
    event = get_object_or_404(Event, pk=event_id)
    congress = get_object_or_404(Congress, pk=congress_id)

    # Check if already entered or entering for someone else
    if not enter_for_another and event.already_entered(request.user):
        return redirect(
            "events:edit_event_entry", event_id=event.id, congress_id=event.congress.id
        )

    # Check if entries are open
    if not event.is_open():
        return render(request, "events/players/event_closed.html", {"event": event})

    # Check if full
    if event.is_full():
        return render(request, "events/players/event_full.html", {"event": event})

    # Check if draft
    if congress.status != "Published":
        return render(request, "events/players/event_closed.html", {"event": event})

    if request.method == "POST":
        return enter_event_post(request, congress, event)
    else:
        return enter_event_non_post(event, congress, request, enter_for_another)
