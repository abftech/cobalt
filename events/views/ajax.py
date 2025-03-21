import copy
import json
from json import JSONDecodeError

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.transaction import atomic
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from accounts.models import User, TeamMate, UserAdditionalInfo
from cobalt.settings import TBA_PLAYER, BRIDGE_CREDITS
from events.views.congress_builder import update_event_start_and_end_times
from logs.views import log_event
from notifications.views.core import contact_member, create_rbac_batch_id
from notifications.models import BatchID
from organisations.models import Organisation
from organisations.club_admin_core import is_player_a_member
from payments.views.core import (
    update_account,
    update_organisation,
    get_balance,
)

# from .core import basket_amt_total, basket_amt_paid, basket_amt_this_user_only, basket_amt_owing_this_user_only
from rbac.core import (
    rbac_user_allowed_for_model,
    rbac_get_users_with_role,
)
from rbac.views import rbac_user_has_role, rbac_forbidden
from events.views.core import (
    notify_conveners,
    send_email_to_player_entered_into_event_by_another,
)
from events.models import (
    Congress,
    CONGRESS_TYPES,
    Category,
    CongressMaster,
    Event,
    Session,
    EventEntry,
    EventEntryPlayer,
    BasketItem,
    EventLog,
    EventPlayerDiscount,
    EVENT_PLAYER_FORMAT_SIZE,
    Bulletin,
    PartnershipDesk,
    CongressDownload,
)
from payments.models import MemberTransaction, OrganisationTransaction


def get_all_congress_ajax(request):
    congresses = Congress.objects.order_by("start_date").select_related(
        "congress_master__org"
    )
    congressList = []
    admin = False
    if request.user.is_authenticated:
        (all_access, some_access) = rbac_user_allowed_for_model(
            request.user, "events", "org", "edit"
        )
        if all_access or some_access:
            admin = True
        else:
            admin = False
    else:
        admin = False

    if not admin:
        congresses = congresses.filter(status="Published")

    congress_type_dict = dict(CONGRESS_TYPES)
    for congress in congresses:

        try:
            data_entry = dict()
            data_entry["congress_name"] = congress.name
            data_entry["month"] = congress.start_date.strftime("%B %Y")
            data_entry["run_by"] = congress.congress_master.org.name
            data_entry["congress_start"] = congress.start_date.strftime("%d/%m/%y")
            data_entry["congress_end"] = congress.end_date.strftime("%d/%m/%y")
            data_entry["state"] = congress.congress_master.org.state
            data_entry["status"] = (
                congress.status if admin else "hide"
            )  # congress.status
            data_entry["event_type"] = congress_type_dict.get(
                congress.congress_type, "Not found"
            )
            data_entry["actions"] = {
                "id": congress.id,
                "edit": congress.user_is_convener(request.user) if admin else False,
                "manage": congress.user_is_convener(request.user) if admin else False,
            }
            congressList.append(data_entry)
        # TODO: Fix this bare exception!
        except:  # noqa: E722
            # "some logging here laterh"
            continue

    resp = {"data": congressList}
    return JsonResponse(data=resp, safe=False)


@login_required()
def get_conveners_ajax(request, org_id):
    """returns a list of conveners as html for an organisation"""

    conveners = rbac_get_users_with_role("events.org.%s.edit" % org_id)

    ret = "<ul>"
    for con in conveners:
        ret += "<li>%s" % con
    ret += (
        "</ul><p>These can be changed from the <a href='/organisations/edit/%s' target='_blank'>Organisation Administration Page</p>"
        % org_id
    )

    data_dict = {"data": ret}
    return JsonResponse(data=data_dict, safe=False)


@login_required()
def get_congress_master_ajax(request, org_id):
    """returns a list of congress_masters as html for an organisation"""

    org = get_object_or_404(Organisation, pk=org_id)

    qs = CongressMaster.objects.filter(org=org).distinct("name")

    ret = "<option value=''>-----------"
    for cm in qs:
        ret += f"<option value='{cm.pk}'>{cm.name}</option>"

    data_dict = {"data": ret}
    return JsonResponse(data=data_dict, safe=False)


@login_required()
def get_congress_ajax(request, congress_id):
    """returns a list of congresses as html for an congress_master"""

    master = get_object_or_404(CongressMaster, pk=congress_id)

    qs = Congress.objects.filter(congress_master=master).distinct("name")

    ret = "<option value=''>-----------"
    for cm in qs:
        ret += f"<option value='{cm.id}'>{cm.name}</option>"

    data_dict = {"data": ret}
    return JsonResponse(data=data_dict, safe=False)


@login_required()
def delete_event_ajax(request):
    """Ajax call to delete an event from a congress"""

    if request.method == "GET":
        event_id = request.GET["event_id"]

    event = get_object_or_404(Event, pk=event_id)

    # check access
    role = "events.org.%s.edit" % event.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    open_entries = EventEntry.objects.exclude(entry_status="Cancelled").filter(
        event=event
    )

    if open_entries:
        response_data = {"message": "Error - Event has entries"}
        return JsonResponse({"data": response_data})

    # Delete any cancelled entries
    EventEntry.objects.filter(entry_status="Cancelled").filter(event=event).delete()

    event_name = event.event_name

    event.delete()

    # COB-799 - update any member or organisation transactions referencing this event
    MemberTransaction.objects.filter(event_id=event_id).update(event_id=None)
    OrganisationTransaction.objects.filter(event_id=event_id).update(event_id=None)

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Deleted event {event_name}",
    )

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def delete_category_ajax(request):
    """Ajax call to delete a category from an event"""

    if request.method == "GET":
        category_id = request.GET["category_id"]
        event_id = request.GET["event_id"]

    category = get_object_or_404(Category, pk=category_id)
    event = get_object_or_404(Event, pk=event_id)
    # check access
    role = "events.org.%s.edit" % category.event.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    category.delete()

    # Log it
    EventLog(
        event=event,
        actor=request.user,
        action=f"deleted category '{category.description}'",
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Deleted category '{category}' from {event.href}",
    )

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def edit_category_ajax(request):
    """Ajax call to edit a category in an event"""

    if request.method == "POST":
        category_id = request.POST["category_id"]
        event_id = request.POST["event_id"]
        description = request.POST["description"]

    category = get_object_or_404(Category, pk=category_id)
    event = get_object_or_404(Event, pk=event_id)
    # check access
    role = "events.org.%s.edit" % category.event.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    old_description = category.description
    category.description = description
    category.save()

    # Log it
    EventLog(
        event=event,
        actor=request.user,
        action=f"Edited category from '{old_description}' to '{category.description}'",
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Edited category from '{old_description}' to '{category.description}' in {event.href}",
    )

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def delete_session_ajax(request):
    """Ajax call to delete a session from a congress"""

    if request.method == "GET":
        session_id = request.GET["session_id"]

    session = get_object_or_404(Session, pk=session_id)

    # check access
    role = f"events.org.{session.event.congress.congress_master.org.id}.edit"
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    session.delete()

    update_event_start_and_end_times(session.event)

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Deleted session '{session.session_date} at {session.session_start}' from {session.event.href}'",
    )

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
@require_GET
def fee_for_user_ajax(request):
    """Ajax call to get entry fee for a user in an event"""

    event_id = request.GET["event_id"]
    user_id = request.GET["user_id"]
    actual_team_size = int(request.GET["team_size"])

    event = get_object_or_404(Event, pk=event_id)
    user = get_object_or_404(User, pk=user_id)

    entry_fee, discount, reason, description = event.entry_fee_for(
        user, actual_team_size=actual_team_size
    )

    response_data = {
        "entry_fee": entry_fee,
        "description": description,
        "discount": discount,
        "message": "Success",
    }

    return JsonResponse({"data": response_data})


@login_required()
def payment_options_for_user_ajax(request):
    """Ajax call to get payment methods - basically team mate relationships

    We turn on this option if the other user has allowed the logged in user
    to make payments for them AND they either have auto top up enabled OR
    enough funds taking away events they have already entered but not paid for.
    This could be with ANY user as the person entering.

    e.g. Fred is entering with Bob as his partner. Bob has allowed Fred to
    do this but doesn't have auto top up enabled. Bob has $100 in his account
    and this event will cost $20. Fred already has another event in his
    basket with Bob as his partner for $50. Jane is also entering an event
    with Bob and has $20 for Bob to pay in her basket. Bob's current total
    commitment is $70, so the $20 for this event is okay. If this event was
    $31 then it would fail."""

    if request.method == "GET":
        entering_user_id = request.GET["entering_user_id"]
        other_user_id = request.GET["other_user_id"]
        event_id = request.GET["event_id"]

    # default to no
    reply = False
    response_data = {}

    # check if allowed to use funds
    user = get_object_or_404(User, pk=other_user_id)
    entrant = get_object_or_404(User, pk=entering_user_id)
    allowed = TeamMate.objects.filter(
        user=user, team_mate=entrant, make_payments=True
    ).exists()

    # check if auto topup enabled

    if allowed:
        if user.stripe_auto_confirmed == "On":
            reply = True
        else:

            # check if sufficient balance

            user_balance = get_balance(user)
            user_committed = 0.0
            event = get_object_or_404(Event, pk=event_id)
            entry_fee, discount, reason, description = event.entry_fee_for(user)

            # get all events with user committed
            basket_items = BasketItem.objects.all()
            for basket_item in basket_items:
                already = basket_item.event_entry.evententryplayer_set.filter(
                    player=user
                ).aggregate(Sum("entry_fee"))
                if already["entry_fee__sum"]:  # ignore None response
                    user_committed += float(already["entry_fee__sum"])

            if user_balance - user_committed - float(entry_fee) >= 0.0:
                reply = True
            else:
                if user_committed > 0.0:
                    response_data[
                        "description"
                    ] = f"{user.first_name} has insufficient funds taking into account other pending event entries."
                else:
                    response_data[
                        "description"
                    ] = f"{user.first_name} has insufficient funds."

    if reply:
        response_data["add_entry"] = "their-system-dollars"
        response_data["message"] = "Allowed"
    else:
        response_data["add_entry"] = ""
        response_data["message"] = "Blocked"

    return JsonResponse({"data": response_data})


@login_required()
def add_category_ajax(request):
    """Ajax call to add an event category to an event"""

    if request.method == "POST":
        event_id = request.POST["event_id"]
        text = request.POST["text"]

    event = get_object_or_404(Event, pk=event_id)

    # check access
    role = "events.org.%s.edit" % event.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    # add category
    category = Category(event=event, description=text)
    category.save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Added category '{text}' to {category.event.href}",
    )

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def admin_offsystem_pay_ajax(request):
    """Ajax call to mark an off-system payment as made"""

    if request.method == "POST":
        event_entry_player_id = request.POST["event_entry_player_id"]

    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)

    # check access
    role = (
        "events.org.%s.edit"
        % event_entry_player.event_entry.event.congress.congress_master.org.id
    )
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    # Mark as paid
    event_entry_player.payment_status = "Paid"
    event_entry_player.payment_received = event_entry_player.entry_fee
    # TODO: client side screen to capture who actually paid this so don't need to assume it was the player
    event_entry_player.paid_by = event_entry_player.player
    event_entry_player.save()

    # Delete from players basket if present
    BasketItem.objects.filter(event_entry=event_entry_player.event_entry).delete()

    # Log it
    EventLog(
        event=event_entry_player.event_entry.event,
        actor=request.user,
        action=f"Marked {event_entry_player.player} as paid",
        event_entry=event_entry_player.event_entry,
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Marked {event_entry_player.player.href} as paid in {event_entry_player.event_entry.event.href}",
    )

    # Check if parent complete
    event_entry_player.event_entry.check_if_paid()

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def admin_offsystem_unpay_ajax(request):
    """Ajax call to mark an off-system payment as no longer paid"""

    if request.method == "POST":
        event_entry_player_id = request.POST["event_entry_player_id"]

    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)

    # check access
    role = (
        "events.org.%s.edit"
        % event_entry_player.event_entry.event.congress.congress_master.org.id
    )
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    # Mark as unpaid
    event_entry_player.payment_status = "Unpaid"
    event_entry_player.payment_received = 0
    event_entry_player.save()

    # Log it
    EventLog(
        event=event_entry_player.event_entry.event,
        actor=request.user,
        action=f"Marked {event_entry_player.player} as unpaid",
        event_entry=event_entry_player.event_entry,
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Marked {event_entry_player.player.href} as unpaid in {event_entry_player.event_entry.event.href}",
    )

    # Check if parent complete
    event_entry_player.event_entry.check_if_paid()

    response_data = {}
    response_data["message"] = "Success"
    return JsonResponse({"data": response_data})


@login_required()
def admin_offsystem_pay_pp_ajax(request):
    """Ajax call to mark a pp payment as paid"""

    if request.method == "POST":
        event_entry_player_id = request.POST["event_entry_player_id"]

    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)

    # check access
    role = (
        "events.org.%s.edit"
        % event_entry_player.event_entry.event.congress.congress_master.org.id
    )
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    # Mark as paid
    event_entry_player.payment_status = "Paid"
    event_entry_player.payment_received = event_entry_player.entry_fee
    # TODO: client side screen to capture who actually paid this so don't need to assume it was the player
    event_entry_player.paid_by = event_entry_player.player
    event_entry_player.save()

    # Delete from players basket if present
    BasketItem.objects.filter(event_entry=event_entry_player.event_entry).delete()

    # Log it
    EventLog(
        event=event_entry_player.event_entry.event,
        actor=request.user,
        action=f"Marked {event_entry_player.player} as paid (pp)",
        event_entry=event_entry_player.event_entry,
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Marked {event_entry_player.player.href} as paid (pp) in {event_entry_player.event_entry.event.href}",
    )

    # Check if parent complete
    event_entry_player.event_entry.check_if_paid()

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def admin_offsystem_unpay_pp_ajax(request):
    """Ajax call to mark a pp payment as no longer paid"""

    if request.method == "POST":
        event_entry_player_id = request.POST["event_entry_player_id"]

    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)

    # check access
    role = (
        "events.org.%s.edit"
        % event_entry_player.event_entry.event.congress.congress_master.org.id
    )
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    # Mark as unpaid
    event_entry_player.payment_status = "Unpaid"
    event_entry_player.payment_received = 0
    event_entry_player.save()

    # Log it
    EventLog(
        event=event_entry_player.event_entry.event,
        actor=request.user,
        action=f"Marked {event_entry_player.player} as unpaid (pp)",
        event_entry=event_entry_player.event_entry,
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Marked {event_entry_player.player.href} as unpaid (pp) in {event_entry_player.event_entry.event.href}",
    )

    # Check if parent complete
    event_entry_player.event_entry.check_if_paid()

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def delete_basket_item_ajax(request):
    """Delete an item from a users basket (and delete the event entry)"""

    if request.method == "GET":
        basket_id = request.GET["basket_id"]

    basket_item = get_object_or_404(BasketItem, pk=basket_id)

    if basket_item.player == request.user:

        # Check if payments have been made
        if (
            EventEntryPlayer.objects.filter(event_entry=basket_item.event_entry)
            .exclude(payment_received=0.0)
            .exists()
        ):
            return JsonResponse(
                {
                    "data": {
                        "message": "Payments have been received for this entry. You can cancel it from the edit event screen."
                    }
                }
            )

        basket_item.event_entry.delete()
        basket_item.delete()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="events_delete_basket_item",
            message=f"Deleted basket item for {basket_item.event_entry.event.href}",
        )

        response_data = {"message": "Success"}
        return JsonResponse({"data": response_data})


@login_required()
def admin_player_discount_delete_ajax(request):
    """Delete a player discount record"""

    if request.method == "POST":
        discount_id = request.POST["event_player_discount_id"]

        event_player_discount = get_object_or_404(EventPlayerDiscount, pk=discount_id)

        # check access
        role = (
            "events.org.%s.edit"
            % event_player_discount.event.congress.congress_master.org.id
        )
        if not rbac_user_has_role(request.user, role):
            return rbac_forbidden(request, role)

        # Log it
        EventLog(
            event=event_player_discount.event,
            actor=request.user,
            action=f"Deleted Event Player Discount for {event_player_discount.player}",
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="events_entries_admin",
            message=f"Deleted Event Player Discount for {event_player_discount.player.href}",
        )

        # Delete it
        event_player_discount.delete()

        response_data = {"message": "Success"}

    else:

        response_data = {"message": "Incorrect call"}

    return JsonResponse({"data": response_data})


@login_required()
def check_player_entry_ajax(request):
    """Check if a player is already entered in an event
    and whether the player is a club member if the event is members only

    Returns one of the following messages:
        Not Entered         OK to proceed
        Already Entered     Cannot be entered again
        Not a Member        Not entered, but not a member in a members only event,
                            and user does not have admin rights to override
        Membership Warning  Not entered, but not a member in a members only event,
                            and user has admin rights so could override and enter anyway
    """

    if request.method == "GET":
        member_id = request.GET["member_id"]
        event_id = request.GET["event_id"]

        member = get_object_or_404(User, pk=member_id)
        event = get_object_or_404(Event, pk=event_id)

        if member.id == TBA_PLAYER:
            return JsonResponse({"message": "Not Entered"})

        membership_issue = event.congress.members_only and not is_player_a_member(
            event.congress.congress_master.org,
            member.system_number,
        )

        event_entry = (
            EventEntryPlayer.objects.filter(player=member)
            .filter(event_entry__event=event)
            .exclude(event_entry__entry_status="Cancelled")
            .count()
        )

        if event_entry:
            return JsonResponse({"message": "Already Entered"})
        else:
            if membership_issue:
                if rbac_user_has_role(
                    request.user,
                    f"events.org.{event.congress.congress_master.org.id}.edit",
                ):
                    return JsonResponse({"message": "Membership Warning"})
                else:
                    return JsonResponse({"message": "Not a Member"})
            else:
                return JsonResponse({"message": "Not Entered"})


@login_required()
def check_player_is_member_ajax(request):
    """Check if a player is a member of the events hosting club
    if appropriate

    Returns:
        OK          OK to proceeed
        ERROR       player is not a member and this is a members only event
                    and user does not have admin rights to override
        WARNING     player is not a member and this is a members only event
                    but user has admin rights and could override and enter anyway
    """

    if request.method == "GET":
        member_id = request.GET["member_id"]
        event_id = request.GET["event_id"]

        member = get_object_or_404(User, pk=member_id)
        event = get_object_or_404(Event, pk=event_id)

        if not event.congress.members_only:
            return JsonResponse({"message": "OK"})

        if member.id == TBA_PLAYER:
            return JsonResponse({"message": "OK"})

        if is_player_a_member(event.congress.congress_master.org, member.system_number):
            return JsonResponse({"message": "OK"})
        else:
            if rbac_user_has_role(
                request.user, f"events.org.{event.congress.congress_master.org.id}.edit"
            ):
                return JsonResponse({"message": "WARNING"})
            else:
                return JsonResponse({"message": "ERROR"})


@login_required()
@require_GET
def recalculate_team_fees_ajax(request):
    """
    Recalculate the team entry fees based on the number in the team
    Expects a list of 6 player ids (some of which may be 'Select...')
    Returns a JSON response with the list of recalcualted fees (-1 for any missing players)
    """

    event_id = request.GET["event_id"]
    event = get_object_or_404(Event, pk=event_id)

    players_json = request.GET.get("players")
    player_ids = json.loads(players_json) if players_json else []

    team_size = 0
    players = []
    for player_id in player_ids:
        try:
            player_pk = int(player_id)
            if player_pk >= 2:
                team_size += 1
                players.append(get_object_or_404(User, pk=player_pk))
            else:
                players.append(None)
        except ValueError:
            players.append(None)

    fee_by_player = []
    for player in players:
        if player:
            entry_fee, discount, reason, description = event.entry_fee_for(
                player, actual_team_size=team_size
            )
            fee_by_player.append(
                {
                    "entry_fee": entry_fee,
                    "discount": discount,
                    "reason": reason,
                    "description": description,
                }
            )
        else:
            fee_by_player.append({"entry_fee": -1})

    return JsonResponse({"fee_by_player": fee_by_player})


@login_required()
@require_GET
def get_player_payment_amount_ajax(request):
    """Before we change a player in an entry, see if the old player qualifies for a refund"""

    # Get entry
    event_entry_player_id = request.GET["player_event_entry"]
    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)

    # If a convener has edited this then we may not have a paid_by
    if not event_entry_player.paid_by:
        return JsonResponse({"refund_is_due": 0})

    # Return if no refund due
    if event_entry_player.payment_received == 0:
        return JsonResponse({"refund_is_due": 0})

    # See if this user made this payment
    if event_entry_player.paid_by == request.user:
        payment_made_by_you = 1
    else:
        payment_made_by_you = 0

    # Provide name and amount
    return JsonResponse(
        {
            "refund_is_due": 1,
            "refund_who": f"{event_entry_player.paid_by.full_name}",
            "refund_amount": event_entry_player.payment_received,
            "payment_made_by_you": payment_made_by_you,
        }
    )


@login_required()
@require_GET
@atomic
def give_player_refund_ajax(request):
    """Execute a refund for a player. Called when a user swaps one paid player for another or an admin does"""

    # Get entry
    event_entry_player_id = request.GET["player_event_entry"]
    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)
    event_entry = event_entry_player.event_entry

    # check access on the parent event_entry
    if not event_entry.user_can_change(request.user):
        # Now check if user is a congress admin
        role = f"events.org.{event_entry_player.event_entry.event.congress.congress_master.org.id}.edit"
        if not rbac_user_has_role(request.user, role):
            return JsonResponse({"message": "Access Denied"})

    # check refund is due
    if event_entry_player.payment_received <= 0:
        return JsonResponse({"message": "No refund due"})

    # create payments in org account
    update_organisation(
        organisation=event_entry.event.congress.congress_master.org,
        amount=-event_entry_player.payment_received,
        description=f"Refund to {event_entry_player.paid_by} for {event_entry.event.event_name}",
        payment_type="Refund",
        member=event_entry_player.paid_by,
    )

    # create payment for member
    update_account(
        organisation=event_entry.event.congress.congress_master.org,
        amount=event_entry_player.payment_received,
        description=f"Refund for {event_entry.event}",
        payment_type="Refund",
        member=event_entry_player.paid_by,
    )

    # Log it
    EventLog(
        event=event_entry.event,
        actor=request.user,
        action=f"Refund of {event_entry_player.payment_received:.2f} to {event_entry_player.paid_by}",
        event_entry=event_entry,
    ).save()

    message = f"Refund of {event_entry_player.payment_received:.2f} paid to {event_entry_player.paid_by}"

    event_entry_player.payment_received = 0
    event_entry_player.paid_by = None
    event_entry_player.entry_complete_date = None
    event_entry_player.payment_status = "Unpaid"
    event_entry_player.payment_type = "Unknown"
    event_entry_player.reason = None
    event_entry_player.entry_complete_date = None
    event_entry_player.save()

    # Check status of entry now
    event_entry_player.event_entry.check_if_paid()

    return JsonResponse({"message": message})


@login_required()
@require_GET
def change_player_entry_ajax(request):
    """Change a player in an event. Also update entry_fee if required"""

    member_id = request.GET["member_id"]
    event_entry_player_id = request.GET["player_event_entry"]

    member = get_object_or_404(User, pk=member_id)
    event_entry_player = get_object_or_404(EventEntryPlayer, pk=event_entry_player_id)
    event_entry = get_object_or_404(EventEntry, pk=event_entry_player.event_entry.id)
    event = get_object_or_404(Event, pk=event_entry.event.id)
    congress = get_object_or_404(Congress, pk=event.congress.id)

    # check access on the parent event_entry
    if not event_entry.user_can_change(request.user):
        return JsonResponse({"message": "Access Denied"})

    # Check if this player is changing themselves so we take them away from the entry screen
    user_is_player = request.user == event_entry_player.player

    # update
    old_player = event_entry_player.player
    event_entry_player.player = member
    event_entry_player.save()

    # Log it
    EventLog(
        event=event,
        actor=request.user,
        event_entry=event_entry,
        action=f"Swapped {member} in for {old_player}",
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_change_entry",
        message=f"Changed {old_player.href} to {member.href} in {event.href}",
    )

    # create batch ID
    batch_id = create_rbac_batch_id(
        rbac_role=f"events.org.{congress.congress_master.org.id}.edit",
        organisation=congress.congress_master.org,
        batch_type=BatchID.BATCH_TYPE_ENTRY,
        description=f"Event entry - {congress}",
    )
    batch_size = 2

    # send
    contact_member(
        member=event_entry_player.player,
        msg="Entry to %s" % congress,
        contact_type="Email",
        html_msg=f"{request.user.full_name} has added you to {event}.<br><br>",
        link="/events/view",
        link_text="View Entry",
        subject="Event Entry - %s" % congress,
        batch_id=batch_id,
    )

    # send
    contact_member(
        member=old_player,
        msg="Entry to %s" % congress,
        contact_type="Email",
        html_msg=f"{request.user.full_name} has removed you from {event}.<br><br>",
        link="/events/view",
        subject="Event Entry - %s" % congress,
        batch_id=batch_id,
    )

    # tell the conveners
    email_msg = f"""{request.user.full_name} has changed an entry for {event.event_name} in {congress}.
                  <br><br>
                  <b>{old_player}</b> has been removed.
                  <br><br>
                  <b>{event_entry_player.player}</b> has been added.
                  <br><br>
                  """

    batch_size += notify_conveners(
        congress=congress,
        event=event,
        subject=f"{event} - {event_entry_player.player} added to entry",
        email_msg=email_msg,
        batch_id=batch_id,
    )

    # Check entry fee - they can keep an early entry discount but nothing else
    #    original_entry_fee = event_entry_player.entry_fee

    # default value
    return_html = "Player successfully changed."

    # Check if this is a free entry - player 5 or 6
    if event_entry_player.payment_type == "Free":

        # update the batch_id
        batch_id.batch_size = batch_size
        batch_id.state = BatchID.BATCH_STATE_COMPLETE
        batch_id.save()

        return JsonResponse({"message": "Success", "html": return_html})

    # get the entry fee based upon when the entry was created

    if event_entry.paying_players <= 4:
        # use standard calculation
        entry_fee, discount, reason, description = event.entry_fee_for(
            event_entry_player.player,
            event_entry_player.event_entry.first_created_date.date(),
        )
    else:
        # team of 5.6 and a recalculation has been done, so use number
        # of paying players
        entry_fee, discount, reason, description = event.entry_fee_for(
            event_entry_player.player,
            event_entry_player.event_entry.first_created_date.date(),
            actual_team_size=event_entry.paying_players,
        )

    event_entry_player.entry_fee = entry_fee
    event_entry_player.reason = reason
    event_entry_player.save()

    # adjust for over or under payment after player change

    difference = float(event_entry_player.payment_received) - float(
        event_entry_player.entry_fee
    )

    if difference > 0:  # overpaid
        # create payments in org account
        update_organisation(
            organisation=event_entry_player.event_entry.event.congress.congress_master.org,
            amount=-difference,
            description=f"{event_entry_player.event_entry.event.event_name} - {event_entry_player.paid_by} partial refund",
            payment_type="Refund",
            member=event_entry_player.paid_by,
        )

        # create payment for user
        update_account(
            member=event_entry_player.paid_by,
            amount=difference,
            description=f"Refund for {event_entry_player.event_entry.event.event_name} - {event_entry_player.player}",
            payment_type="Refund",
            organisation=event_entry_player.event_entry.event.congress.congress_master.org,
        )

        # update entry payment amount
        event_entry_player.payment_received = event_entry_player.entry_fee
        event_entry_player.save()

        return_html = f"Player successfully changed. A refund of {difference} credits was paid to {event_entry_player.paid_by}"

        # Log it
        EventLog(
            event=event,
            actor=request.user,
            event_entry=event_entry,
            action=f"Triggered refund for {member} - {difference} credits",
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="events_entries_admin",
            message=f"Triggered refund for {member.href} - {difference} credits in {event.href}",
        )

        # notify member of refund
        contact_member(
            member=event_entry_player.paid_by,
            msg="Refund from - %s" % event,
            contact_type="Email",
            html_msg=f"A refund of {difference} credits has been made to your {BRIDGE_CREDITS} accounts from {event}.<br><br>",
            link="/events/view",
            subject="Refund from  %s" % event,
            batch_id=batch_id,
        )
        batch_size += 1

        # tell the conveners
        msg = f"""{event_entry_player.paid_by.full_name} has been refunded
                      {difference} {BRIDGE_CREDITS} for {event.event_name} in {congress}
                      due to change of player from {old_player} to {event_entry_player.player}.
                      <br><br>
                      """
        batch_size += notify_conveners(
            congress,
            event,
            f"{event} - {event_entry_player.paid_by} refund",
            msg,
            batch_id=batch_id,
        )

    # if money is owing then update paid status on event_entry
    if difference < 0:
        difference = -difference
        event_entry_player.payment_status = "Unpaid"
        event_entry_player.save()
        event_entry.check_if_paid()
        return_html = f"Player successfully changed. There are {difference:.2f} credits required for this player entry."

    # Check if payment status should be paid. e.g. enter as Youth and swap to another, then back to Youth
    if event_entry_player.entry_fee == event_entry_player.payment_received:
        event_entry_player.payment_status = "Paid"
        event_entry_player.save()
        event_entry.check_if_paid()

    # update the batch_id
    batch_id.batch_size = batch_size
    batch_id.state = BatchID.BATCH_STATE_COMPLETE
    batch_id.save()

    # the HTML screen reloads but we need to tell the user what happened first
    # Also if the player has just deleted themselves then take them back to the dashboard
    return JsonResponse(
        {"message": "Success", "html": return_html, "user_is_player": user_is_player}
    )


@login_required()
def add_player_to_existing_entry_ajax(request):
    """Add a player to a team from the edit entry screen"""

    if request.method == "GET":
        event_entry_id = request.GET["event_entry_id"]
        event_entry = get_object_or_404(EventEntry, pk=event_entry_id)

        # check access
        if not event_entry.user_can_change(request.user):
            return JsonResponse({"message": "Access Denied"})

        # check if already full
        event_entry_player_count = (
            EventEntryPlayer.objects.filter(event_entry=event_entry)
            .exclude(event_entry__entry_status="Cancelled")
            .count()
        )

        if (
            event_entry_player_count
            >= EVENT_PLAYER_FORMAT_SIZE[event_entry.event.player_format]
        ):
            return JsonResponse({"message": "Maximum player number reached"})

        # if we got here everything is okay, create new player
        # this will always be the 5th or 6th player in a team and will be free
        event_entry_player = EventEntryPlayer()
        tba = get_object_or_404(User, pk=TBA_PLAYER)
        event_entry_player.player = tba
        event_entry_player.event_entry = event_entry
        event_entry_player.entry_fee = 0
        event_entry_player.payment_status = "Free"
        event_entry_player.payment_type = "Free"
        event_entry_player.save()

        # log it
        EventLog(
            event=event_entry.event,
            actor=request.user,
            action="Added a player",
            event_entry=event_entry,
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="events_change_entry",
            message=f"Added 5/6 player to {event_entry_player.event_entry.event.href}",
        )

        return JsonResponse({"message": "Success"})


@login_required()
@require_GET
def recalculate_team_fees_on_edit_ajax(request):
    """Recalculate team entry fees, called from player edit entry"""

    event_entry_id = request.GET["event_entry_id"]
    event_entry = get_object_or_404(EventEntry, pk=event_entry_id)

    # check access
    if not event_entry.user_can_change(request.user):
        return JsonResponse({"message": "Access Denied"})

    # check ok to recalcualte (should not be called if not, but to be safe)
    if not event_entry.can_recalculate:
        return JsonResponse({"message": "Recalculation not permitted"})

    if not event_entry.recalculate_fees():
        # fails if not ok to recalcualte (should not be called if not, but to be safe)
        return JsonResponse({"message": "Recalculation not permitted"})

    return JsonResponse({"message": "Success"})


@login_required()
def delete_player_from_entry_ajax(request):
    """Delete a player (5 or 6 only) from a team from the edit entry screen"""

    if request.method == "GET":
        event_entry_player_id = request.GET["event_entry_player_id"]
        event_entry_player = get_object_or_404(
            EventEntryPlayer, pk=event_entry_player_id
        )

        # check access
        if not event_entry_player.event_entry.user_can_change(request.user):
            return JsonResponse({"message": "Access Denied"})

        # check if extra player
        event_entry_player_count = (
            EventEntryPlayer.objects.filter(event_entry=event_entry_player.event_entry)
            .exclude(event_entry__entry_status="Cancelled")
            .count()
        )

        if event_entry_player_count < 5:
            return JsonResponse({"message": "Not an extra player. Cannot delete."})

        # log it
        EventLog(
            event=event_entry_player.event_entry.event,
            actor=request.user,
            action=f"Deleted {event_entry_player.player} from team",
            event_entry=event_entry_player.event_entry,
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="events_change_entry",
            message=f"Deleted {event_entry_player.player.href} from {event_entry_player.event_entry.event.href}",
        )

        # if we got here everything is okay
        old_event_entry_player = copy.copy(event_entry_player)

        # If anything has been paid then change player to TBA, else delete
        if event_entry_player.payment_received > 0.0:
            tba = User.objects.get(pk=TBA_PLAYER)
            event_entry_player.player = tba
            event_entry_player.save()
        else:
            event_entry_player.delete()

        if old_event_entry_player.player.id != TBA_PLAYER:

            event = old_event_entry_player.event_entry.event
            congress = old_event_entry_player.event_entry.event.congress

            # create batch ID
            batch_id = create_rbac_batch_id(
                rbac_role=f"events.org.{congress.congress_master.org.id}.edit",
                organisation=congress.congress_master.org,
                batch_type=BatchID.BATCH_TYPE_ENTRY,
                description=f"Removal from {event}",
                complete=True,
            )
            batch_size = 1

            # notify member
            contact_member(
                member=old_event_entry_player.player,
                msg="Removal from %s" % event,
                contact_type="Email",
                html_msg=f"{request.user.full_name} has removed you from their team in {event}.<br><br>",
                link="/events/view",
                subject="Removal from %s" % event,
                batch_id=batch_id,
            )

            # tell the conveners
            msg = f"""{old_event_entry_player.player.full_name} has been removed from the team
                      by {request.user.full_name} for {event.event_name} in {congress}.
                      <br><br>
                      The team is still complete.
                      <br><br>
                      """
            batch_size += notify_conveners(
                congress,
                event,
                f"{event} - Extra player {old_event_entry_player.player} removed",
                msg,
                batch_id=batch_id,
            )

            # update the batch_id
            batch_id.batch_size = batch_size
            batch_id.state = BatchID.BATCH_STATE_COMPLETE
            batch_id.save()

        return JsonResponse({"message": "Success"})


@login_required()
def change_category_on_existing_entry_ajax(request, event_entry_id, category_id):

    event_entry = get_object_or_404(EventEntry, pk=event_entry_id)
    category = get_object_or_404(Category, pk=category_id)

    if not event_entry.user_can_change(request.user):
        return JsonResponse({"message": "Access Denied"})

    # log it
    EventLog(
        event=event_entry.event,
        actor=request.user,
        action=f"Changed category to {category} from {event_entry.category}",
        event_entry=event_entry,
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_change_entry",
        message=f"Changed category to {category} from {event_entry.category} in {event_entry.event.href}",
    )

    # create batch ID
    batch_id = create_rbac_batch_id(
        rbac_role=f"events.org.{event_entry.event.congress.congress_master.org.id}.edit",
        organisation=event_entry.event.congress.congress_master.org,
        batch_type=BatchID.BATCH_TYPE_ENTRY,
        description=f"{event_entry.event} - {request.user.full_name} Changed category",
        complete=True,
    )

    # tell the conveners
    email_msg = f"""{request.user.full_name} has changed an entry for {event_entry.event.event_name} in {event_entry.event.congress}.
              <br><br>
              <b>Changed category to {category} from {event_entry.category}.
              <br><br>
              """

    batch_size = notify_conveners(
        congress=event_entry.event.congress,
        event=event_entry.event,
        subject=f"{event_entry.event} - {request.user.full_name} Changed category",
        email_msg=email_msg,
        batch_id=batch_id,
    )

    # update the batch_id
    batch_id.batch_size = batch_size
    batch_id.state = BatchID.BATCH_STATE_COMPLETE
    batch_id.save()

    event_entry.category = category
    event_entry.save()

    return JsonResponse({"message": "Success"})


@login_required()
def change_answer_on_existing_entry_ajax(request, event_entry_id, answer):
    """Update the answer to the question on entry"""

    event_entry = get_object_or_404(EventEntry, pk=event_entry_id)

    if not event_entry.user_can_change(request.user):
        return JsonResponse({"message": "Access Denied"})

    # log it
    EventLog(
        event=event_entry.event,
        actor=request.user,
        action=f"Changed answer to {answer} from {event_entry.free_format_answer}",
        event_entry=event_entry,
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_change_entry",
        message=f"Changed answer to {answer} from {event_entry.free_format_answer} in {event_entry.event.href}",
    )

    event_entry.free_format_answer = answer
    event_entry.save()

    return JsonResponse({"message": "Success"})


@login_required()
def admin_delete_bulletin_ajax(request):
    """Ajax call to delete a bulletin from a congress"""

    if request.method == "GET":
        bulletin_id = request.GET["bulletin_id"]

    bulletin = get_object_or_404(Bulletin, pk=bulletin_id)

    # check access
    role = "events.org.%s.edit" % bulletin.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Deleted bulletin {bulletin} from {bulletin.congress.href}",
    )

    bulletin.delete()

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def admin_delete_download_ajax(request):
    """Ajax call to delete a download from a congress"""

    if request.method == "GET":
        download_id = request.GET["download_id"]

    download = get_object_or_404(CongressDownload, pk=download_id)

    # check access
    role = "events.org.%s.edit" % download.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_admin",
        message=f"Deleted a download document {download} from {download.congress.href}",
    )

    download.delete()

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def delete_me_from_partnership_desk(request, event_id):
    """delete this user from the partnership desk"""

    event = get_object_or_404(Event, pk=event_id)

    partnership = (
        PartnershipDesk.objects.filter(player=request.user).filter(event=event).first()
    )

    if partnership:
        # Log it
        EventLog(
            event=event,
            actor=request.user,
            action="Deleted partnership desk listing",
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="partnership_desk",
            message=f"Deleted partnership desk listing from {event.href}",
        )

        partnership.delete()

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def contact_partnership_desk_person_ajax(request):
    """get in touch with someone who you want to play with from the partnership desk"""

    if request.method == "GET":
        partnership_desk_id = request.GET["partnership_desk_id"]
        partnership_desk = get_object_or_404(PartnershipDesk, pk=partnership_desk_id)
        message = request.GET["message"]

        # Log it
        EventLog(
            event=partnership_desk.event,
            actor=request.user,
            action=f"Shared partnership desk details with {partnership_desk.player}",
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="partnership_desk",
            message=f"Shared partnership desk details with {partnership_desk.player.href}",
        )

        email_body = f"""{request.user} has responded to your partnership desk search.<br><br>
                        <h3>Message</h3>
                        {message}<br><br>
                        <h3>Details</h3>
                        Event: {partnership_desk.event}<br>
                        Email: <a href="mailto:{request.user.email}">{request.user.email}</a><br>
                        Phone: {request.user.mobile}<br><br>
        """

        # send
        contact_member(
            member=partnership_desk.player,
            msg="Partnership Message from %s" % request.user.full_name,
            contact_type="Email",
            html_msg=email_body,
            link="/events/view",
            subject="Partnership Message",
        )

    response_data = {"message": "Success"}
    return JsonResponse({"data": response_data})


@login_required()
def change_payment_method_on_existing_entry_ajax(request):
    """Ajax call from edit event entry screen to change payment method"""

    if request.method == "GET":
        player_entry_id = request.GET["player_entry_id"]
        payment_method = request.GET["payment_method"]

        player_entry = get_object_or_404(EventEntryPlayer, pk=player_entry_id)

        # Check access
        if not player_entry.event_entry.user_can_change(request.user):
            return JsonResponse({"message": "Access Denied"})

        player_entry.payment_type = payment_method
        if payment_method in ["bank-transfer", "cash", "cheque"]:
            player_entry.payment_status = "Pending Manual"
        else:
            player_entry.payment_status = "Unpaid"

        player_entry.save()

        # Log it
        EventLog(
            event=player_entry.event_entry.event,
            actor=request.user,
            action=f"Changed payment method for {player_entry.player} to {payment_method}",
            event_entry=player_entry.event_entry,
        ).save()

        log_event(
            user=request.user,
            severity="INFO",
            source="Events",
            sub_source="change_event_entry",
            message=f"Changed payment method to {payment_method} for {player_entry.event_entry.event.href}",
        )

        # If changed to ask them to pay ie other-system-dollars, then notify the player who needs to pay
        if payment_method == "other-system-dollars":
            player = player_entry.player
            event_entry = player_entry.event_entry
            event = event_entry.event
            congress = event.congress
            event_entry_players = EventEntryPlayer.objects.filter(
                event_entry=event_entry
            )
            send_email_to_player_entered_into_event_by_another(
                player=player,
                congress=congress,
                event_entry_players=event_entry_players,
                struct={player: {congress: {event: event_entry_players}}},
                event_entries=[event_entry],
                payment_user=request.user,
                triggered_by_team_mate_payment=False,
                team_mate_who_triggered=request.user,
            )

        return JsonResponse({"message": "Success"})

    return JsonResponse({"message": "Invalid call"})


@login_required()
def admin_event_entry_notes_ajax(request):
    """Ajax call from event entry screen to update notes"""

    if request.method != "POST":
        return JsonResponse({"message": "Invalid call"})

    data = json.loads(request.body.decode("utf-8"))
    event_entry_id = int(data["id"])
    notes = data["notes"]

    event_entry = get_object_or_404(EventEntry, pk=event_entry_id)

    # check access
    role = "events.org.%s.edit" % event_entry.event.congress.congress_master.org.id
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    print("notes", notes)

    event_entry.notes = None if len(notes) == 0 else notes
    event_entry.save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="events_entries_admin",
        message=f"Added notes '{notes}' to {event_entry.href} in {event_entry.event.href}",
    )

    return JsonResponse({"message": "Success"})


@login_required()
def edit_comment_event_entry_ajax(request):
    """Edit comment on an event entry"""

    if request.method != "POST":
        return JsonResponse({"message": "Invalid call"})

    data = json.loads(request.body.decode("utf-8"))
    event_entry_id = int(data["id"])
    event_entry = get_object_or_404(EventEntry, pk=event_entry_id)
    new_comment = data["comment"]
    event_entry.comment = new_comment
    event_entry.save()

    # Log it
    EventLog(
        event=event_entry.event,
        actor=request.user,
        action=f"Changed comment to '{new_comment}' on {event_entry}",
    ).save()

    log_event(
        user=request.user,
        severity="INFO",
        source="Events",
        sub_source="change_event_entry",
        message=f"Changed comment to '{new_comment}' on {event_entry.href}",
    )

    return JsonResponse({"message": "Success"})


@login_required()
def edit_team_name_event_entry_ajax(request):
    """Edit team name on an event entry"""

    if request.method != "POST":
        return JsonResponse({"message": "Invalid call"})

    data = json.loads(request.body.decode("utf-8"))
    event_entry_id = int(data["id"])
    event_entry = get_object_or_404(EventEntry, pk=event_entry_id)

    event_entry_player_me = (
        EventEntryPlayer.objects.filter(event_entry=event_entry)
        .filter(player=request.user)
        .exists()
    )

    if not event_entry_player_me and event_entry.primary_entrant != request.user:
        return JsonResponse({"message": "You cannot edit this entry"})

    new_team_name = data["team_name"]

    # Don't store empty string, use None
    if new_team_name == "":
        new_team_name = None

    event_entry.team_name = new_team_name
    event_entry.save()

    # Log it
    EventLog(
        event_entry=event_entry,
        event=event_entry.event,
        actor=request.user,
        action=f"Changed team name to '{new_team_name}' on {event_entry}",
    ).save()

    return JsonResponse({"message": "Success"})


@login_required()
def save_congress_view_filters_ajax(request):
    """Save a users preferences for viewing congresses"""

    # Get data
    state = request.POST.get("state")
    congress_type = request.POST.get("congress_type")
    congress_venue_type = request.POST.get("congress_venue_type")
    search_string = request.POST.get("search_string")
    preferences = {
        "state": state,
        "congress_type": congress_type,
        "congress_venue_type": congress_venue_type,
        "search_string": search_string,
    }

    # save
    user_additional_info, _ = UserAdditionalInfo.objects.get_or_create(
        user=request.user
    )
    user_additional_info.congress_view_filters = json.dumps(preferences)
    user_additional_info.save()

    return HttpResponse()


@login_required()
def clear_congress_view_filters_ajax(request):
    """Clear a users preferences for viewing congresses"""

    user_additional_info, _ = UserAdditionalInfo.objects.get_or_create(
        user=request.user
    )
    user_additional_info.congress_view_filters = ""
    user_additional_info.save()

    return HttpResponse()


@login_required()
def load_congress_view_filters_ajax(request):
    """load a users preferences for viewing congresses"""

    user_additional_info = UserAdditionalInfo.objects.filter(user=request.user).first()

    if not user_additional_info:
        return HttpResponse()

    try:
        preferences = json.loads(user_additional_info.congress_view_filters)
    except JSONDecodeError:
        return HttpResponse()

    return JsonResponse(preferences)
