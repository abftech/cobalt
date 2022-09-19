from decimal import Decimal

from django.db.models import Sum, Max, F
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from accounts.accounts_views.core import (
    get_user_or_unregistered_user_from_system_number,
)
from accounts.models import User, UnregisteredUser
from cobalt.settings import (
    BRIDGE_CREDITS,
    GLOBAL_CURRENCY_SYMBOL,
    ALL_SYSTEM_ACCOUNTS,
    GLOBAL_ORG,
)
from masterpoints.views import abf_checksum_is_valid
from notifications.notifications_views.core import (
    send_cobalt_email_to_system_number,
)
from organisations.models import (
    Organisation,
    MemberMembershipType,
    MiscPayType,
    ClubLog,
)
from organisations.views.general import get_membership_type_for_players
from payments.models import OrgPaymentMethod, MemberTransaction, UserPendingPayment
from payments.payments_views.core import (
    org_balance,
    update_account,
    update_organisation,
)
from payments.payments_views.payments_api import payment_api_batch

from rbac.views import rbac_forbidden
from rbac.core import rbac_user_has_role
from .common import SITOUT, VISITOR, PLAYING_DIRECTOR
from .decorators import user_is_club_director

from ..forms import SessionForm, UserSessionForm
from ..models import (
    Session,
    SessionEntry,
    SessionTypePaymentMethodMembership,
    SessionMiscPayment,
)


def bridge_credits_for_club(club):
    """return the bridge credits payment method for a club"""

    return OrgPaymentMethod.objects.filter(
        active=True, organisation=club, payment_method="Bridge Credits"
    ).first()


def iou_for_club(club):
    """return the IOU payment method for a club"""

    return OrgPaymentMethod.objects.filter(
        active=True, organisation=club, payment_method="IOU"
    ).first()


@login_required()
def new_session(request, club_id):
    """Set up a new bridge session for a club"""

    club = get_object_or_404(Organisation, pk=club_id)

    club_role = f"club_sessions.sessions.{club.id}.edit"
    if not rbac_user_has_role(request.user, club_role):
        return rbac_forbidden(request, club_role)

    # Set up form values
    director_name = request.user.full_name

    # Load form
    session_form = SessionForm(
        request.POST or None, club=club, initial={"director": request.user}
    )

    if request.method == "POST" and session_form.is_valid():
        session = session_form.save(commit=False)
        session.club = club
        session.save()
        return redirect("club_sessions:manage_session", session_id=session.id)
    else:
        print(session_form.errors)

    return render(
        request,
        "club_sessions/new/new_session.html",
        {
            "club": club,
            "session_form": session_form,
            "director_name": director_name,
            "new_or_edit": "new",
        },
    )


@login_required()
def manage_session(request, session_id):
    """Main page to manage a club session after it has been created"""

    session = get_object_or_404(Session, pk=session_id)

    club = get_object_or_404(Organisation, pk=session.session_type.organisation.id)

    club_role = f"club_sessions.sessions.{club.id}.edit"
    if not rbac_user_has_role(request.user, club_role):
        return rbac_forbidden(request, club_role)

    has_session_entries = SessionEntry.objects.filter(session=session).exists()

    return render(
        request,
        "club_sessions/manage/manage_session.html",
        {"club": club, "session": session, "has_session_entries": has_session_entries},
    )


def _handle_change_secondary_payment_method(
    old_method, new_method, session, club, administrator
):
    """make changes when the secondary payment method is updated"""

    session_entries = SessionEntry.objects.filter(
        session=session, payment_method=old_method
    ).exclude(system_number__in=[PLAYING_DIRECTOR, SITOUT])
    for session_entry in session_entries:
        session_entry.payment_method = new_method
        session_entry.save()

        # Handle IOUs
        if new_method.payment_method == "IOU":
            _handle_iou_changes_on(club, session_entry, administrator)

        if old_method.payment_method == "IOU":
            _handle_iou_changes_off(club, session_entry)

    if session_entries:
        message = f"Updated {len(session_entries)} player payment methods."
    else:
        message = "Form saved. No player payment methods were changed."

    return message


def _handle_change_additional_session_fee_reason(old_reason, new_reason, session, club):
    """Handle the settings being changed for additional fees - change the reason"""

    session_entries = SessionEntry.objects.filter(session=session).exclude(
        system_number__in=[PLAYING_DIRECTOR, SITOUT]
    )

    for session_entry in session_entries:

        SessionMiscPayment.objects.filter(
            session_entry=session_entry,
            description=old_reason,
        ).update(description=new_reason)


def _handle_change_additional_session_fee(old_fee, new_fee, session, club, old_reason):
    """Handle the settings being changed for additional fees"""

    bridge_credits = bridge_credits_for_club(club)
    iou = iou_for_club(club)

    message = ""

    session_entries = SessionEntry.objects.filter(session=session).exclude(
        system_number__in=[PLAYING_DIRECTOR, SITOUT]
    )

    for session_entry in session_entries:

        if old_fee == 0:
            # Create new entries from scratch
            SessionMiscPayment(
                session_entry=session_entry,
                description=session.additional_session_fee_reason,
                payment_method=session_entry.payment_method,
                amount=new_fee,
            ).save()

        elif new_fee == 0:
            # Delete entries without bridge credits or ious
            SessionMiscPayment.objects.filter(session_entry=session_entry).filter(
                description=old_reason
            ).exclude(payment_method__in=[bridge_credits, iou]).delete()

            # Handle bridge credits and IOUs
            if (
                SessionMiscPayment.objects.filter(session_entry=session_entry)
                .filter(description=old_reason)
                .filter(payment_method__in=[bridge_credits, iou])
                .exists()
            ):
                message = f" Some entries have paid with {BRIDGE_CREDITS} or IOUs. You need to handle these manually."
            else:
                message = "Additional fees removed."

        else:
            # Update entries without bridge credits or ious
            SessionMiscPayment.objects.filter(session_entry=session_entry).filter(
                description=old_reason
            ).exclude(payment_method__in=[bridge_credits, iou]).update(
                amount=new_fee, payment_made=False
            )

            # Handle bridge credits and IOUs
            if (
                SessionMiscPayment.objects.filter(session_entry=session_entry)
                .filter(description=old_reason)
                .filter(payment_method__in=[bridge_credits, iou])
                .exists()
            ):
                message = f" Some entries have paid with {BRIDGE_CREDITS} or IOUs. You need to handle these manually."
            else:
                message = "Additional fees changed."

    return message


@user_is_club_director()
def tab_settings_htmx(request, club, session):
    """Edit fields that were set up when the session was started"""

    message = ""

    if "save_settings" in request.POST:
        session_form = SessionForm(request.POST, club=club, instance=session)

        # Save old values in case we need them below
        old_payment_method = session.default_secondary_payment_method
        old_additional_session_fee = session.additional_session_fee
        old_additional_session_fee_reason = session.additional_session_fee_reason

        if session_form.is_valid():
            session = session_form.save()
            message = "Session Updated"

            if "additional_session_fee" in session_form.changed_data:
                message += _handle_change_additional_session_fee(
                    old_fee=old_additional_session_fee,
                    new_fee=session_form.cleaned_data["additional_session_fee"],
                    session=session,
                    club=club,
                    old_reason=old_additional_session_fee_reason,
                )

            if "additional_session_fee_reason" in session_form.changed_data:
                _handle_change_additional_session_fee_reason(
                    old_additional_session_fee_reason,
                    session.additional_session_fee_reason,
                    session,
                    club,
                )

            if "default_secondary_payment_method" in session_form.changed_data:
                message += _handle_change_secondary_payment_method(
                    old_method=old_payment_method,
                    new_method=session_form.cleaned_data[
                        "default_secondary_payment_method"
                    ],
                    session=session,
                    club=club,
                    administrator=request.user,
                )
        else:
            print(session_form.errors)

    session_form = SessionForm(club=club, instance=session)

    director_name = f"{session.director}"

    response = render(
        request,
        "club_sessions/manage/settings_htmx.html",
        {
            "session_form": session_form,
            "club": club,
            "session": session,
            "message": message,
            "director_name": director_name,
        },
    )

    # Reload sessions tab if we change anything
    if "save_settings" in request.POST:
        response["HX-Trigger"] = "reload_sessions"

    return response


def load_session_entry_static(session, club):
    """Sub of tab_session_htmx. Load the data we need to be able to process the session tab"""

    # Get the entries for this session
    session_entries = SessionEntry.objects.filter(session=session)

    # Map to Users or UnregisteredUsers

    # Get system numbers
    system_number_list = session_entries.values_list("system_number")

    # Get Users and UnregisteredUsers
    users = User.objects.filter(system_number__in=system_number_list)
    un_regs = UnregisteredUser.objects.filter(system_number__in=system_number_list)

    # Convert to a dictionary
    mixed_dict = {}

    for user in users:
        user.is_user = True
        mixed_dict[user.system_number] = {
            "type": "User",
            "value": user,
            "icon": "account_circle",
        }

    # Add unregistered to dictionary
    for un_reg in un_regs:
        un_reg.is_un_reg = True
        mixed_dict[un_reg.system_number] = {
            "type": "UnregisteredUser",
            "value": un_reg,
            "icon": "stars",
        }

    # Get memberships
    membership_type_dict = get_membership_type_for_players(system_number_list, club)

    # Add visitor
    membership_type_dict[VISITOR] = "Guest"

    # Load session fees
    session_fees = _get_session_fees_for_club(club)

    return session_entries, mixed_dict, session_fees, membership_type_dict


def _get_session_fees_for_club(club):
    """return session fees as a dictionary. We use the name of the membership as the key, not the number

    e.g. session_fees = {"Standard": {"EFTPOS": 5, "Cash": 12}}

    """

    fees = SessionTypePaymentMethodMembership.objects.filter(
        session_type_payment_method__session_type__organisation=club
    )

    session_fees = {}
    for fee in fees:
        membership_name = "Guest" if fee.membership is None else fee.membership.name
        if membership_name not in session_fees:
            session_fees[membership_name] = {}
        session_fees[membership_name][
            fee.session_type_payment_method.payment_method.payment_method
        ] = fee.fee

    return session_fees


def _get_extras_as_total_for_session_entries(
    session, paid_only=False, unpaid_only=False
):
    """get the total amount of extras for each session entry as a dictionary

    paid_only - only included total for extras that have been paid for
    unpaid_only - only included total for extras that have not been paid for

    """
    extras_qs = (
        SessionMiscPayment.objects.filter(session_entry__session=session)
        .values("session_entry")
        .annotate(extras=Sum("amount"))
    )

    if paid_only:
        extras_qs = extras_qs.filter(payment_made=True)

    if unpaid_only:
        extras_qs = extras_qs.filter(payment_made=False)

    # convert to dict
    return {item["session_entry"]: float(item["extras"]) for item in extras_qs}


def _get_extras_for_session_entries(session_entries):
    """get the extras associated with a queryset of SessionEntries"""

    session_entries_list = session_entries.values_list("id", flat=True)
    extras = SessionMiscPayment.objects.filter(
        session_entry__in=session_entries_list
    ).values("session_entry", "amount")
    extras_dict = {}
    for extra in extras:
        if extra["session_entry"] not in extras_dict:
            extras_dict[extra["session_entry"]] = extra["amount"]
        else:
            extras_dict[extra["session_entry"]] += extra["amount"]

    return extras_dict


def _augment_session_entries_process_entry(
    session_entry, mixed_dict, membership_type_dict, extras_dict, valid_payment_methods
):
    """sub of _augment_session_entries to handle a single session entry"""

    # table
    if session_entry.pair_team_number % 2 == 0:
        session_entry.table_colour = "even"
    else:
        session_entry.table_colour = "odd"

    # Add User or UnregisterUser to the entry and note the player_type
    if session_entry.system_number == SITOUT:
        # Sit out
        session_entry.player_type = "NotRegistered"
        session_entry.icon = "hourglass_empty"
        session_entry.player = {"full_name": "Sitout", "first_name": "Sitout"}
        icon_text = "There is nobody at this position"
    elif session_entry.system_number == PLAYING_DIRECTOR:
        # Playing Director
        session_entry.player_type = "NotRegistered"
        session_entry.icon = "local_police"
        session_entry.player = {
            "full_name": "PLAYING DIRECTOR",
            "first_name": "DIRECTOR",
        }
        icon_text = "Playing Director"
    elif session_entry.system_number == VISITOR:
        # Visitor with no ABF number
        session_entry.player_type = "NotRegistered"
        session_entry.icon = "handshake"
        session_entry.player = {
            "full_name": session_entry.player_name_from_file.title(),
            "first_name": session_entry.player_name_from_file.split(" ")[0].title(),
        }
        icon_text = f"Non-{GLOBAL_ORG} Member"
    elif session_entry.system_number in mixed_dict:
        session_entry.player = mixed_dict[session_entry.system_number]["value"]
        session_entry.player_type = mixed_dict[session_entry.system_number]["type"]
        session_entry.icon = mixed_dict[session_entry.system_number]["icon"]
        icon_text = f"{session_entry.player.first_name} is "

    else:
        session_entry.player_type = "NotRegistered"
        session_entry.icon = "error"
        session_entry.player = {"full_name": "Unknown"}
        icon_text = "This person is "

    # membership
    if session_entry.system_number == SITOUT:
        # Sit out
        session_entry.membership = "Guest"
    elif session_entry.system_number in membership_type_dict:
        # This person is a member
        session_entry.membership = membership_type_dict[session_entry.system_number]
        session_entry.membership_type = "member"
        session_entry.icon_colour = "primary"
        if session_entry.system_number not in [SITOUT, PLAYING_DIRECTOR, VISITOR]:
            icon_text += f"a {session_entry.membership} member."
    else:
        # Not a member
        session_entry.membership = "Guest"
        if session_entry.system_number not in [SITOUT, PLAYING_DIRECTOR, VISITOR]:
            icon_text += "a Guest."
        if session_entry.system_number >= 0 and abf_checksum_is_valid(
            session_entry.system_number
        ):
            session_entry.membership_type = "Valid Number"
            session_entry.icon_colour = "warning"
        else:
            session_entry.membership_type = "Invalid Number"
            session_entry.icon_colour = "dark"

    # valid payment method. In list of valid is fine, or simple not set is fine too
    if session_entry.payment_method:
        session_entry.payment_method_is_valid = (
            session_entry.payment_method.payment_method in valid_payment_methods
        )
    else:
        session_entry.payment_method_is_valid = True

    # Add icon text
    session_entry.icon_text = icon_text

    # Add extras
    session_entry.extras = extras_dict.get(session_entry.id, 0)

    return session_entry


def _augment_session_entries(
    session_entries, mixed_dict, membership_type_dict, session_fees, club
):
    """Sub of tab_Session_htmx. Adds extra values to the session_entries for display by the template

    Players can be:
        Users
        UnregisteredUsers
        Nothing

        If Nothing, they can have a valid ABF number, an invalid ABF number or no ABF number

    Their relationship with the club can be:
        Member
        Non-member

    """

    # The payment method may no longer be valid, we want to flag this
    valid_payment_methods = OrgPaymentMethod.objects.filter(
        organisation=club, active=True
    ).values_list("payment_method", flat=True)

    # Get any extra payments as a dictionary
    extras_dict = _get_extras_for_session_entries(session_entries)

    # Now add the object to the session list, also add colours for alternate tables
    for session_entry in session_entries:

        session_entry = _augment_session_entries_process_entry(
            session_entry,
            mixed_dict,
            membership_type_dict,
            extras_dict,
            valid_payment_methods,
        )

    # work out payment method and if user has sufficient funds
    return _calculate_payment_method_and_balance(session_entries, session_fees, club)


def _calculate_payment_method_and_balance(session_entries, session_fees, club):
    """work out who can pay by bridge credits and if they have enough money"""

    # First build list of users who are bridge credit eligible
    bridge_credit_users = []
    for session_entry in session_entries:
        if session_entry.player_type == "User" and session_entry.system_number not in [
            ALL_SYSTEM_ACCOUNTS
        ]:
            bridge_credit_users.append(session_entry.system_number)

    # Now get their balances
    balances = {
        member_transaction.member: member_transaction.balance
        for member_transaction in MemberTransaction.objects.filter(
            member__system_number__in=bridge_credit_users
        )
    }

    bridge_credit_payment_method = OrgPaymentMethod.objects.filter(
        organisation=club, payment_method=BRIDGE_CREDITS, active=True
    ).first()

    # Go through and add balance to session entries
    for session_entry in session_entries:
        if session_entry.player_type == "User":
            # if not in balances then it is zero
            session_entry.balance = balances.get(session_entry.player, 0)

            # Only change payment method to Bridge Credits if not set to something already
            if not session_entry.payment_method:
                session_entry.payment_method = bridge_credit_payment_method

        # fee due
        if (
            session_entry.payment_method
            and not session_entry.fee
            and not session_entry.system_number == PLAYING_DIRECTOR
        ):
            session_entry.fee = session_fees[session_entry.membership][
                session_entry.payment_method.payment_method
            ]

        session_entry.save()

        if session_entry.fee:
            session_entry.total = session_entry.fee + session_entry.extras
        else:
            session_entry.total = "NA"
    return session_entries


@user_is_club_director()
def tab_session_htmx(request, club, session, message="", bridge_credit_failures=None):
    """present the main session tab for the director

    We have 3 different views (Summary, Detail, Table) but we generate them all from this function.

    That means there are some things calculated that aren't needed for a view, but it keeps it simple.

    """

    if bridge_credit_failures is None:
        bridge_credit_failures = []

    # load static
    (
        session_entries,
        mixed_dict,
        session_fees,
        membership_type_dict,
    ) = load_session_entry_static(session, club)

    # augment the session_entries
    session_entries = _augment_session_entries(
        session_entries, mixed_dict, membership_type_dict, session_fees, club
    )

    # get payment methods for this club
    payment_methods = OrgPaymentMethod.objects.filter(organisation=club, active=True)

    # Which template to use - summary, detail or table. Default is summary.
    view_type = request.POST.get("view_type", "summary")
    view_options = {
        "summary": "club_sessions/manage/session_summary_view_htmx.html",
        "detail": "club_sessions/manage/session_detail_view_htmx.html",
        "table": "club_sessions/manage/session_table_view_htmx.html",
    }
    template = view_options[view_type]

    if view_type == "detail":
        # Too hard for the template, so set up allowed payment methods for dropdown in the view
        session_entries = _tab_session_htmx_payment_methods(
            session_entries, session, payment_methods
        )

    if view_type == "summary":
        payment_summary = _tab_session_htmx_summary_table(
            session, session_entries, mixed_dict, membership_type_dict
        )
    else:
        payment_summary = {}

    # Handle table view
    if view_type == "table":
        table_list, table_status = _tab_session_htmx_table_view(
            session, session_entries
        )
    else:
        table_list = {}
        table_status = {}

    return render(
        request,
        template,
        {
            "club": club,
            "session": session,
            "session_entries": session_entries,
            "table_list": table_list,
            "table_status": table_status,
            "payment_methods": payment_methods,
            "payment_summary": payment_summary,
            "message": message,
            "bridge_credit_failures": bridge_credit_failures,
        },
    )


def _tab_session_htmx_payment_methods(session_entries, session, payment_methods):
    """logic is too complicated for a template, so build the payment_methods here for each session_entry

    Only allow IOU for properly registered users
    Don't allow changes to bridge credits if already paid for
    Don't show bridge credits as an option if we have already processed them

    """

    for session_entry in session_entries:
        # paid for with credits, no change allowed
        if (
            session_entry.payment_method
            and session_entry.payment_method.payment_method == BRIDGE_CREDITS
            and session_entry.amount_paid > 0
        ):
            session_entry.payment_methods = [session_entry.payment_method]
        # if we have processed the bridge credits already, then don't allow bridge credits as an option
        elif session.status in [
            Session.SessionStatus.COMPLETE,
            Session.SessionStatus.CREDITS_PROCESSED,
        ]:
            session_entry.payment_methods = []
            for payment_method in payment_methods:
                if payment_method.payment_method != BRIDGE_CREDITS and (
                    session_entry.player_type == "User"
                    or payment_method.payment_method != "IOU"
                ):
                    session_entry.payment_methods.append(payment_method)
        else:
            session_entry.payment_methods = []
            for payment_method in payment_methods:
                if (
                    session_entry.player_type == "User"
                    or payment_method.payment_method != "IOU"
                ):
                    session_entry.payment_methods.append(payment_method)

    return session_entries


def _tab_session_htmx_table_view(session, session_entries):
    """handle formatting for the table view"""

    extras = _get_extras_as_total_for_session_entries(session)

    table_list = {}
    table_status = {}
    # put session_entries into a dictionary for the table view
    for session_entry in session_entries:

        # Add to dict if not present
        if session_entry.pair_team_number not in table_list:
            table_list[session_entry.pair_team_number] = []
            table_status[session_entry.pair_team_number] = True

        session_entry.extras = Decimal(extras.get(session_entry.id, 0))
        # Add extras to entry fee for this view, no good reason
        session_entry.fee += session_entry.extras

        table_list[session_entry.pair_team_number].append(session_entry)
        if session_entry.fee > session_entry.amount_paid:
            # unpaid entry, mark table as incomplete
            table_status[session_entry.pair_team_number] = False

    return table_list, table_status


def _tab_session_htmx_summary_table(
    session, session_entries, mixed_dict, membership_type_dict
):
    """summarise session_entries for the summary view"""

    extras_paid = _get_extras_as_total_for_session_entries(session, paid_only=True)
    extras_unpaid = _get_extras_as_total_for_session_entries(session, unpaid_only=True)
    extras = _get_extras_as_total_for_session_entries(session)

    payment_summary = {}
    for session_entry in session_entries:
        # Skip sitout and director
        if session_entry.system_number in [SITOUT, PLAYING_DIRECTOR]:
            continue

        if session_entry.payment_method:
            pay_method = session_entry.payment_method.payment_method
        else:
            pay_method = "Unknown"

        # Add to dict if not present
        if session_entry.payment_method.payment_method not in payment_summary:
            payment_summary[pay_method] = {
                "fee": Decimal(0),
                "amount_paid": Decimal(0),
                "outstanding": Decimal(0),
                "player_count": 0,
                "players": [],
            }

        # Update dict with this session_entry
        payment_summary[pay_method]["fee"] += session_entry.fee + Decimal(
            extras.get(session_entry.id, 0)
        )
        payment_summary[pay_method]["amount_paid"] += session_entry.amount_paid
        payment_summary[pay_method]["outstanding"] += (
            session_entry.fee
            + Decimal(extras_unpaid.get(session_entry.id, 0))
            - session_entry.amount_paid
        )
        payment_summary[pay_method]["player_count"] += 1

        # Add session_entry as well for drop down list
        name = mixed_dict[session_entry.system_number]["value"]
        member_type = membership_type_dict.get(session_entry.system_number, "Guest")
        session_entry.fee += Decimal(extras.get(session_entry.id, 0))
        session_entry.amount_paid += Decimal(extras_paid.get(session_entry.id, 0))
        # Handle visitors
        if session_entry.system_number == VISITOR:
            name = session_entry.player_name_from_file.title()

        item = {
            "player": name,
            "session_entry": session_entry,
            "membership": member_type,
        }
        payment_summary[pay_method]["players"].append(item)

    return payment_summary


def _edit_session_entry_handle_post(request, club, session_entry):
    """Sub for edit_session_entry_htmx to handle the form being posted"""

    message = "Data saved"

    form = UserSessionForm(request.POST, club=club, session_entry=session_entry)
    if not form.is_valid():
        print(form.errors)
        return form, "There were errors on the form"

    # get user type
    is_user = request.POST.get("is_user")
    is_un_reg = request.POST.get("is_un_reg")

    # Handle session data
    session_entry.fee = form.cleaned_data["fee"]
    if form.cleaned_data["is_paid"]:
        session_entry.amount_paid = session_entry.fee
    else:
        session_entry.amount_paid = 0
    payment_method = OrgPaymentMethod.objects.get(
        pk=form.cleaned_data["payment_method"]
    )

    # Handle player being changed
    new_user_id = form.cleaned_data["player_no"]
    system_number = None
    if new_user_id:
        if is_user:
            system_number = User.objects.get(pk=new_user_id).system_number
        elif is_un_reg:
            system_number = UnregisteredUser.objects.get(pk=new_user_id).system_number
    if system_number:
        session_entry.system_number = system_number

    # Handle IOUs and bridge_credits
    if "payment_method" in form.changed_data:
        _handle_iou_changes(payment_method, club, session_entry, request.user)

        # Handle bridge credits being changed to something else
        if is_user:
            status, message = _handle_bridge_credit_changes(
                payment_method, club, session_entry, request.user, message
            )

    session_entry.payment_method = payment_method
    session_entry.save()

    # reset form and return
    form = UserSessionForm(club=club, session_entry=session_entry)

    return form, message


def _handle_iou_changes(payment_method, club, session_entry, administrator):
    """handle the payment type toggling between IOU and something else"""

    # Check for turning on
    if payment_method.payment_method == "IOU":
        _handle_iou_changes_on(club, session_entry, administrator)

    # Check for turning off
    if session_entry.payment_method.payment_method == "IOU":
        _handle_iou_changes_off(club, session_entry)


def _handle_iou_changes_on(club, session_entry, administrator):
    """Handle turning on an IOU"""

    # For safety ensure we don't duplicate
    user_pending_payment, _ = UserPendingPayment.objects.get_or_create(
        organisation=club,
        system_number=session_entry.system_number,
        session_entry=session_entry,
        amount=session_entry.fee,
        description=session_entry.session.description,
    )
    user_pending_payment.save()

    subject = f"Pending Payment to {club}"
    message = f"""
    {administrator.full_name} has recorded you as entering {session_entry.session} but not paying.
    That is fine, you can pay later.
    <br><br>
    The amount owing is {GLOBAL_CURRENCY_SYMBOL}{session_entry.fee}.
    <br><br>
    If you believe this to be incorrect please contact {club} directly in the first instance.
    """

    send_cobalt_email_to_system_number(
        session_entry.system_number,
        subject,
        message,
        club=club,
        administrator=administrator,
    )

    session_entry.amount_paid = session_entry.fee
    session_entry.save()


def _handle_iou_changes_off(club, session_entry):
    """Turn off using an IOU"""

    print("Off")

    UserPendingPayment.objects.filter(
        organisation=club,
        system_number=session_entry.system_number,
        session_entry=session_entry,
    ).delete()


def _handle_bridge_credit_changes(
    payment_method, club, session_entry, director, message
):
    """When the director changes payment method from bridge credit to something else, we need to handle refunds
    if payment already made.

    If they change from something else to Bridge Credits then we need to change the status of the session.

    Returns:
        status(boolean): is it okay to continue, True/False
        message(str): message to return to user, can be empty

    """

    bridge_credit_payment_method = bridge_credits_for_club(club)

    if (
        session_entry.payment_method != bridge_credit_payment_method
        and payment_method != bridge_credit_payment_method
    ):
        # No bridge credits involved (not old payment method or new)
        return True, message

    if (
        session_entry.payment_method == bridge_credit_payment_method
        and session_entry.amount_paid > 0
    ):
        return _handle_bridge_credit_changes_refund(
            club, session_entry, director, message
        )

    if payment_method == bridge_credit_payment_method:
        # New payment method is bridge credits. Force status to be pending bridge credits
        session_entry.session.status = Session.SessionStatus.DATA_LOADED
        session_entry.session.save()

        # Mark entry as unpaid - don't drop paid extras though
        session_entry.amount_paid = 0
        for misc_payments in SessionMiscPayment.objects.filter(
            session_entry=session_entry, payment_method=bridge_credit_payment_method
        ):
            if misc_payments.payment_made:
                session_entry.amount_paid += misc_payments.amount
        session_entry.save()
        return True, message

    else:
        # Was bridge credits, but isn't now. Mark as unpaid
        session_entry.amount_paid = 0
        session_entry.save()


def _handle_bridge_credit_changes_refund(club, session_entry, director, message):
    # Refund needed
    if org_balance(club) < session_entry.amount_paid:
        return False, "Club has insufficient funds for this refund"

    player = User.objects.filter(system_number=session_entry.system_number).first()

    update_account(
        member=player,
        amount=session_entry.amount_paid,
        description=f"{BRIDGE_CREDITS} returned for {session_entry.session}",
        payment_type="Refund",
        organisation=club,
    )

    update_organisation(
        organisation=club,
        amount=-session_entry.amount_paid,
        description=f"{BRIDGE_CREDITS} returned for {session_entry.session}",
        payment_type="Refund",
        member=player,
    )

    # log it
    ClubLog(
        organisation=club,
        actor=director,
        action=f"Refunded {player} {GLOBAL_CURRENCY_SYMBOL}{session_entry.amount_paid:.2f} for session",
    ).save()

    return True, "Player refunded"


@user_is_club_director(include_session_entry=True)
def edit_session_entry_htmx(request, club, session, session_entry):
    """Edit a single session_entry on the session page

    We hide a lot of extra things in the form for this view

    The most significant changes involve Bridge Credits - if credits have been paid and we change to another
    payment method, then we need to make a refund.

    """

    # See if POSTed form or not
    if "save_session" in request.POST:
        form, message = _edit_session_entry_handle_post(request, club, session_entry)
    else:
        form = UserSessionForm(club=club, session_entry=session_entry)
        message = ""

    # Check if payment method used is still valid
    valid_payment_methods = [item[1] for item in form.fields["payment_method"].choices]

    # unset or in the list are both valid
    if session_entry.payment_method:
        payment_method_is_valid = (
            session_entry.payment_method.payment_method in valid_payment_methods
        )
    else:
        payment_method_is_valid = True

    response = render(
        request,
        "club_sessions/manage/edit_session_entry_htmx.html",
        {
            "club": club,
            "session": session,
            "session_entry": session_entry,
            "form": form,
            "message": message,
            "payment_method_is_valid": payment_method_is_valid,
        },
    )

    # We might have changed the status of the session, so reload totals
    # response["HX-Trigger"] = "update_totals"

    return response


@user_is_club_director(include_session_entry=True)
def edit_session_entry_extras_htmx(request, club, session, session_entry, message=""):
    """Handle the extras part of the session entry edit screen - IOUs, misc payments etc"""

    # get this orgs miscellaneous payment types and payment methods
    misc_payment_types = MiscPayType.objects.filter(organisation=club)
    payment_methods = OrgPaymentMethod.objects.filter(active=True, organisation=club)

    # get misc payments for this user through the extended info table
    #    misc_payments_for_user =

    # Check for IOUs from any club
    user_pending_payments = UserPendingPayment.objects.filter(
        system_number=session_entry.system_number
    )

    # Get any existing misc payments for this session
    session_misc_payments = SessionMiscPayment.objects.filter(
        session_entry=session_entry
    )

    player = get_user_or_unregistered_user_from_system_number(
        session_entry.system_number
    )

    return render(
        request,
        "club_sessions/manage/edit_session_entry_extras_htmx.html",
        {
            "misc_payment_types": misc_payment_types,
            "payment_methods": payment_methods,
            "user_pending_payments": user_pending_payments,
            "session_entry": session_entry,
            "session": session,
            "player": player,
            "club": club,
            "session_misc_payments": session_misc_payments,
            "message": message,
        },
    )


@user_is_club_director(include_session_entry=True)
def change_payment_method_htmx(request, club, session, session_entry):
    """called when the payment method dropdown is changed on the session tab"""

    payment_method = get_object_or_404(
        OrgPaymentMethod, pk=request.POST.get("payment_method")
    )

    # Handle IOUs
    # TODO: HANDLE IOUs

    # Get the membership_type for this user and club, None means they are a guest
    member_membership_type = (
        MemberMembershipType.objects.filter(system_number=session_entry.system_number)
        .filter(membership_type__organisation=club)
        .first()
    )

    if member_membership_type:
        member_membership = member_membership_type.membership_type
    else:
        member_membership = None  # Guest

    fee = SessionTypePaymentMethodMembership.objects.filter(
        session_type_payment_method__session_type__organisation=club,
        session_type_payment_method__payment_method=payment_method,
        membership=member_membership,
    ).first()

    session_entry.payment_method = payment_method
    session_entry.fee = fee.fee
    session_entry.save()

    return HttpResponse(fee.fee)


@user_is_club_director(include_session_entry=True)
def change_paid_amount_status_htmx(request, club, session, session_entry):
    """Change the status of the amount paid for a user. We simply toggle the paid amount from 0 to full amount"""

    if session_entry.amount_paid == session_entry.fee:
        session_entry.amount_paid = 0
        session_entry.save()
        if (
            session_entry.payment_method
            and session_entry.payment_method.payment_method == "IOU"
        ):
            _handle_iou_changes_off(club, session_entry)
    else:
        session_entry.amount_paid = session_entry.fee or 0
        session_entry.save()
        if (
            session_entry.payment_method
            and session_entry.payment_method.payment_method == "IOU"
        ):
            _handle_iou_changes_on(club, session_entry, request.user)

    # Check status now
    unpaid_count = (
        SessionEntry.objects.filter(session=session)
        .exclude(amount_paid=F("fee"))
        .count()
    )
    if unpaid_count > 1:
        return HttpResponse("")

    elif unpaid_count == 0:
        # No unpaid, mark as complete
        session.status = Session.SessionStatus.COMPLETE
        session.save()

    elif unpaid_count == 1:
        # one unpaid, so either un-ticked, or ticked second last. reset status
        session.status = Session.SessionStatus.CREDITS_PROCESSED
        session.save()

    # Include HX-Trigger in response so we know to update the totals too
    response = HttpResponse("")
    response["HX-Trigger"] = "update_totals"
    return response


def _session_totals_calculations(
    session, session_entries, session_fees, membership_type_dict
):
    """sub of session_totals_htmx to build dict of totals"""

    # initialise totals
    totals = {
        "tables": 0,
        "players": 0,
        "unknown_payment_methods": 0,
        "bridge_credits_due": 0,
        "bridge_credits_received": 0,
        "other_methods_due": 0,
        "other_methods_received": 0,
    }

    # go through entries and update totals
    for session_entry in session_entries:

        # ignore missing players
        if session_entry.system_number == SITOUT:
            continue

        totals["players"] += 1

        # handle unknown payment methods
        if not session_entry.payment_method:
            totals["unknown_payment_methods"] += 1
            continue

        # we only store system_number on the session_entry. Need to look up amount due via membership type for
        # this system number and the session_fees for this club for each membership type

        # It is also possible that the static data has changed since this was created, so we need to
        # handle the session_fees not existing for this payment_method

        # Get membership for user, if not found then this will be a Guest
        membership_for_this_user = membership_type_dict.get(
            session_entry.system_number, "Guest"
        )

        if session_entry.fee:
            # If fee is set then use that
            this_fee = session_entry.fee
        else:
            # Otherwise, try to look it up
            try:
                this_fee = session_fees[membership_for_this_user][
                    session_entry.payment_method.payment_method
                ]
            except KeyError:
                # if that fails default to 0 - will mean the static has changed since we set the payment_method
                # and this payment method is no longer in use. 0 seems a good default
                this_fee = 0

        # Update totals
        if session_entry.payment_method.payment_method == BRIDGE_CREDITS:
            totals["bridge_credits_due"] += this_fee
            totals["bridge_credits_received"] += session_entry.amount_paid
        else:
            totals["other_methods_due"] += this_fee
            totals["other_methods_received"] += session_entry.amount_paid

    totals["tables"] = totals["players"] / 4

    return totals


@user_is_club_director()
def session_totals_htmx(request, club, session):
    """Calculate totals for a session and return formatted header over htmx. Repeats a lot of what
    happens for loading the session tab in the first place."""

    # load static
    (
        session_entries,
        mixed_dict,
        session_fees,
        membership_type_dict,
    ) = load_session_entry_static(session, club)

    # augment the session_entries
    session_entries = _augment_session_entries(
        session_entries, mixed_dict, membership_type_dict, session_fees, club
    )

    # do calculations
    session_entries = _calculate_payment_method_and_balance(
        session_entries, session_fees, club
    )

    # calculate totals
    totals = _session_totals_calculations(
        session, session_entries, session_fees, membership_type_dict
    )

    # Progress
    if session.status == Session.SessionStatus.DATA_LOADED:
        progress_colour = "danger"
        progress_percent = 20
    elif session.status == Session.SessionStatus.CREDITS_PROCESSED:
        progress_colour = "warning"
        progress_percent = 60
    elif session.status == Session.SessionStatus.COMPLETE:
        progress_colour = "success"
        progress_percent = 100

    # Get bridge credits for this org
    bridge_credits = bridge_credits_for_club(club)

    # See if anyone is paying with bridge credits
    paying_with_bridge_credits = any(
        session_entry.payment_method == bridge_credits
        for session_entry in session_entries
    )

    return render(
        request,
        "club_sessions/manage/totals_htmx.html",
        {
            "totals": totals,
            "session": session,
            "club": club,
            "progress_colour": progress_colour,
            "progress_percent": progress_percent,
            "paying_with_bridge_credits": paying_with_bridge_credits,
        },
    )


@user_is_club_director(include_session_entry=True)
def add_misc_payment_htmx(request, club, session, session_entry):
    """Adds a miscellaneous payment for a user in a session"""

    # load data from form
    misc_description = request.POST.get("misc_description")
    amount = float(request.POST.get("amount"))
    payment_method = get_object_or_404(
        OrgPaymentMethod, pk=request.POST.get("payment_method")
    )

    # validate
    if amount <= 0:
        return edit_session_entry_extras_htmx(
            request, message="Amount must be greater than zero"
        )

    # load member
    member = get_user_or_unregistered_user_from_system_number(
        session_entry.system_number
    )
    if not member:
        return edit_session_entry_extras_htmx(request, message="Error loading member")

    # Add misc payment
    session_misc_payment = SessionMiscPayment(
        session_entry=session_entry,
        description=misc_description,
        payment_method=payment_method,
        amount=amount,
    )
    session_misc_payment.save()

    message = f"{misc_description} added"

    # If payments have been made for this session_entry and it was bridge credits, then try to
    # process this now
    bridge_credits = bridge_credits_for_club(club)

    if (
        session_misc_payment.payment_method == bridge_credits
        and session_entry.amount_paid > 0
    ):
        if payment_api_batch(
            member=member,
            description=f"{session} - {session_misc_payment.description}",
            amount=amount,
            organisation=club,
            payment_type="Club Payment",
            session=session,
        ):
            session_misc_payment.payment_made = True
            session_misc_payment.save()
            message += " and payment made."

        else:
            # Failed payment. Cancel it.
            session_misc_payment.delete()
            message = "Payment failed. Try another payment method."

    return edit_session_entry_extras_htmx(request, message=message)


@user_is_club_director()
def process_bridge_credits_htmx(request, club, session):
    """handle bridge credits for the session - called from a big button"""

    # Get bridge credits for this org
    bridge_credits = bridge_credits_for_club(club)

    if not bridge_credits:
        return tab_session_htmx(
            request,
            message="Bridge Credits are not set up for this organisation. Add through Settings if you wish to use Bridge Credits",
        )

    # Get any extras
    extras = _get_extras_as_total_for_session_entries(session)

    # For each player go through and work out what they owe
    session_entries = SessionEntry.objects.filter(
        session=session, amount_paid=0, payment_method=bridge_credits
    ).exclude(system_number__in=ALL_SYSTEM_ACCOUNTS)

    # Go back if no bridge credits being paid
    if not session_entries:
        session.status = Session.SessionStatus.CREDITS_PROCESSED
        session.save()
        message = f"No {BRIDGE_CREDITS} to process. Moving to Off-System Payments."

    else:
        success, failures = _process_bridge_credits_sub(
            session_entries, session, club, bridge_credits, extras
        )
        message = (
            f"{BRIDGE_CREDITS} processed. Success: {success}. Failure {len(failures)}."
        )

    # Include HX-Trigger in response so we know to update the totals too
    response = tab_session_htmx(
        request, message=message, bridge_credit_failures=failures
    )
    response["HX-Trigger"] = "update_totals"
    return response


def _process_bridge_credits_sub(session_entries, session, club, bridge_credits, extras):
    """sub of process_bridge_credits_htmx to handle looping through and making payments"""

    # counters
    success = 0
    failures = []

    # users
    system_numbers = session_entries.values_list("system_number", flat=True)
    users_qs = User.objects.filter(system_number__in=system_numbers)
    users_by_system_number = {user.system_number: user for user in users_qs}

    # loop through and try to make payments
    for session_entry in session_entries:

        amount_paid = (
            float(session_entry.amount_paid) if session_entry.amount_paid else 0
        )
        fee = float(session_entry.fee) if session_entry.fee else 0
        amount = fee - amount_paid + extras.get(session_entry.id, 0)

        # Add comments to statement if extras are included
        if extras.get(session_entry.id):
            description = f"{session} plus extras"
        else:
            description = f"{session}"

        # Try payment
        member = users_by_system_number[session_entry.system_number]
        if payment_api_batch(
            member=member,
            description=description,
            amount=amount,
            organisation=club,
            payment_type="Club Payment",
            session=session,
        ):
            # Success
            success += 1
            session_entry.amount_paid = session_entry.fee
            session_entry.save()

            # mark any misc payments for this session as paid
            SessionMiscPayment.objects.filter(
                session_entry__session=session,
                session_entry__system_number=session_entry.system_number,
            ).update(payment_made=True, payment_method=bridge_credits)

        else:
            # Payment failed - change payment method
            failures.append(member)
            session_entry.payment_method = session.default_secondary_payment_method
            session_entry.save()

    # Update status of session - see if there are any payments left
    if (
        SessionEntry.objects.filter(session=session)
        .exclude(payment_method=bridge_credits)
        .exists()
    ):
        session.status = Session.SessionStatus.CREDITS_PROCESSED
    else:
        # No further payments, move to next step
        session.status = Session.SessionStatus.COMPLETE
    session.save()

    return success, failures


@user_is_club_director(include_session_entry=True)
def delete_misc_session_payment_htmx(request, club, session, session_entry):
    """Delete a misc session payment"""

    # Get data
    session_misc_payment = get_object_or_404(
        SessionMiscPayment, pk=request.POST.get("session_misc_payment_id")
    )

    # validate
    if session_misc_payment.session_entry != session_entry:
        return edit_session_entry_extras_htmx(
            request, message="Misc payment not for this session"
        )

    # handle already paid
    if session_misc_payment.payment_made:
        return edit_session_entry_extras_htmx(
            request, message="Payment already made. Handle later"
        )

    # delete
    session_misc_payment.delete()
    return edit_session_entry_extras_htmx(
        request, message="Miscellaneous payment deleted"
    )


@user_is_club_director()
def add_table_htmx(request, club, session):
    """Add a table to a session"""

    try:
        last_table = (
            SessionEntry.objects.filter(session=session).aggregate(
                Max("pair_team_number")
            )["pair_team_number__max"]
            + 1
        )
    except TypeError:
        last_table = 1

    for direction in ["N", "S", "E", "W"]:
        SessionEntry(
            session=session,
            pair_team_number=last_table,
            system_number=SITOUT,
            seat=direction,
            amount_paid=0,
        ).save()

    return tab_session_htmx(request, message="Table added")


@user_is_club_director()
def process_off_system_payments_htmx(request, club, session):
    """mark all off system payments as paid - called from a big button"""

    # Get bridge credits for this org
    bridge_credits = bridge_credits_for_club(club)

    # Get session entries
    session_entries = SessionEntry.objects.filter(session=session).exclude(
        payment_method=bridge_credits
    )

    # Get any extras
    extras = _get_extras_as_total_for_session_entries(session)

    for session_entry in session_entries:
        session_entry.amount_paid = session_entry.fee + Decimal(
            extras.get(session_entry.id, 0)
        )
        session_entry.save()

        # mark misc payments for this session as paid
        SessionMiscPayment.objects.filter(
            session_entry__session=session,
            session_entry__system_number=session_entry.system_number,
        ).update(payment_made=True, payment_method=session_entry.payment_method)

    session.status = Session.SessionStatus.COMPLETE
    session.save()

    # Include HX-Trigger in response so we know to update the totals too
    response = tab_session_htmx(request, message="Off System payments made")
    response["HX-Trigger"] = "update_totals"
    return response
