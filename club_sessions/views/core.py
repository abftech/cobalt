# Define some constants
from decimal import Decimal

from django.db.models import Sum, Max

from accounts.models import User, UnregisteredUser
from club_sessions.models import (
    SessionEntry,
    SessionTypePaymentMethodMembership,
    SessionMiscPayment,
    Session,
)
from cobalt.settings import (
    GLOBAL_ORG,
    ALL_SYSTEM_ACCOUNTS,
    BRIDGE_CREDITS,
    GLOBAL_CURRENCY_SYMBOL,
)
from masterpoints.factories import masterpoint_factory_creator
from masterpoints.views import abf_checksum_is_valid
from notifications.views.core import send_cobalt_email_to_system_number
from organisations.models import ClubLog, Organisation
from organisations.views.general import (
    get_membership_type_for_players,
    get_membership_for_player,
)
from payments.models import OrgPaymentMethod, MemberTransaction, UserPendingPayment
from payments.views.core import (
    org_balance,
    update_account,
    update_organisation,
)
from payments.views.payments_api import payment_api_batch

PLAYING_DIRECTOR = 1
SITOUT = -1
VISITOR = 0


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
    session_fees = get_session_fees_for_club(club)

    return session_entries, mixed_dict, session_fees, membership_type_dict


def get_session_fees_for_club(club):
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


def get_session_fee_for_player(session_entry: SessionEntry, club: Organisation):
    """return correct fee for a player"""

    if session_entry.system_number in [PLAYING_DIRECTOR, SITOUT]:
        return Decimal(0)

    # Get membership. None for Guests
    membership = get_membership_for_player(session_entry.system_number, club)

    session_type_payment_method_membership = (
        SessionTypePaymentMethodMembership.objects.filter(
            session_type_payment_method__payment_method=session_entry.payment_method
        )
        .filter(membership=membership)
        .first()
    )

    return session_type_payment_method_membership.fee


def get_extras_as_total_for_session_entries(
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


def get_extras_for_session_entries(session_entries):
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


def augment_session_entries_process_entry(
    session_entry, mixed_dict, membership_type_dict, extras_dict, valid_payment_methods
):
    """sub of augment_session_entries to handle a single session entry"""

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
            "full_name": "Playing Director",
            "first_name": "Director",
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

    # valid payment method. In list of valid is fine, or simply not set is fine too
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


def augment_session_entries(
    session_entries, mixed_dict, membership_type_dict, session_fees, club
):
    """Sub of tab_session_htmx. Adds extra values to the session_entries for display by the template

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
    extras_dict = get_extras_for_session_entries(session_entries)

    # Now add the object to the session list, also add colours for alternate tables
    for session_entry in session_entries:
        session_entry = augment_session_entries_process_entry(
            session_entry,
            mixed_dict,
            membership_type_dict,
            extras_dict,
            valid_payment_methods,
        )

    # work out payment method and if user has sufficient funds
    return calculate_payment_method_and_balance(session_entries, session_fees, club)


def calculate_payment_method_and_balance(session_entries, session_fees, club):
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

    bridge_credit_payment_method = bridge_credits_for_club(club)

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
            and session_entry.system_number not in [PLAYING_DIRECTOR, SITOUT]
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


def edit_session_entry_handle_ious(
    club,
    session_entry,
    administrator,
    old_payment_method,
    new_payment_method,
    old_fee,
    new_fee,
    old_is_paid,
    new_is_paid,
    message="",
):
    """handle the director changing anything on a session entry that relates to IOUs"""

    iou = iou_for_club(club)
    bridge_credits = bridge_credits_for_club(club)

    # Check for changing amount on already paid IOU
    if (
        new_payment_method == iou
        and old_payment_method == iou
        and old_is_paid
        and old_fee != new_fee
    ):
        return (
            f"{message}Cannot change amount of a paid IOU. You may need to do this in two steps.",
            session_entry,
        )

    # Check for turning on - can happen by changing payment method with paid flag on, or by just changing the flag
    if (new_payment_method == iou and old_payment_method != iou and new_is_paid) or (
        new_payment_method == iou
        and old_payment_method == iou
        and new_is_paid
        and not old_is_paid
    ):
        session_entry.payment_method = new_payment_method
        session_entry.fee = new_fee
        session_entry.is_paid = True
        session_entry.save()
        handle_iou_changes_on(club, session_entry, administrator)
        return f"{message} IOU set up.", session_entry

    # Check for turning off - can be change of type or change of flag
    if (new_payment_method != iou and old_payment_method == iou and old_is_paid) or (
        new_payment_method == iou
        and old_payment_method == iou
        and old_is_paid
        and not new_is_paid
    ):
        session_entry.payment_method = new_payment_method
        session_entry.fee = new_fee

        # Watch out for bridge credits - don't accidentally mark as paid
        if new_payment_method != bridge_credits:
            session_entry.is_paid = new_is_paid

        session_entry.save()
        handle_iou_changes_off(club, session_entry)
        return f"{message}IOU deleted.", session_entry

    # Shouldn't get here
    return f"{message}An error occurred", session_entry


def handle_iou_changes_on(club, session_entry, administrator):
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

    session_entry.is_paid = True
    session_entry.save()


def handle_iou_changes_off(club, session_entry):
    """Turn off using an IOU"""

    # TODO: What about IOU extras?

    UserPendingPayment.objects.filter(
        organisation=club,
        system_number=session_entry.system_number,
        session_entry=session_entry,
    ).delete()


def edit_session_entry_handle_bridge_credits(
    club,
    session,
    session_entry,
    director,
    is_user,
    old_payment_method,
    new_payment_method,
    old_fee,
    new_fee,
    old_is_paid,
    new_is_paid,
):
    """Handle a director making any changes to an entry that involve bridge credits.

    Returns:
        message(str): message to return to user, can be empty
        session_entry(SessionEntry)

    """

    if not is_user:
        return "Player is not a registered user.", session_entry

    # If this isn't paid, and we change it then no problem
    if not old_is_paid and not new_is_paid:
        session_entry.payment_method = new_payment_method
        session_entry.fee = new_fee
        session_entry.save()
        return "Data saved", session_entry

    # Get Bridge Credits
    bridge_credit_payment_method = bridge_credits_for_club(club)

    # if it was paid using bridge credits, and we change the fee, block the change
    if (
        old_payment_method == bridge_credit_payment_method
        and old_is_paid
        and old_fee != new_fee
    ):
        return (
            "Cannot change the amount of an entry paid with Bridge Credits. You may need to do this in two steps, "
            "or use Extras.",
            session_entry,
        )

    # if it has gone from unpaid to paid, and new_payment_method is bridge credits, then pay it and any extras
    if (
        new_payment_method == bridge_credit_payment_method
        and new_is_paid
        and not old_is_paid
    ):
        session_entry.fee = new_fee
        session_entry.payment_method = new_payment_method

        member = User.objects.filter(system_number=session_entry.system_number).first()

        if not member:
            return "Error retrieving user", session_entry

        # Get all of the unpaid bridge credit extras
        extras = SessionMiscPayment.objects.filter(
            session_entry=session_entry,
            payment_made=False,
            payment_method=bridge_credit_payment_method,
        )

        # Get total amount of the extras
        extras_total = extras.values("session_entry").annotate(extras=Sum("amount"))

        amount = session_entry.fee

        if extras_total:
            amount += extras_total[0]["extras"]

        status = payment_api_batch(
            member=member,
            description=f"{session}",
            amount=amount,
            organisation=club,
            payment_type="Club Payment",
            session=session,
        )

        if status:

            # Worked so mark this as paid
            session_entry.is_paid = True
            session_entry.save()

            # mark the extras as paid
            extras.update(payment_made=True)

            return "Payment made", session_entry

        else:

            # failed. Now we have an unpaid bridge credit so change status of session as well
            session_entry.is_paid = False
            session_entry.save()
            session_entry.session.status = Session.SessionStatus.DATA_LOADED
            session_entry.session.save()

            return "Payment failed", session_entry

    # If we have changed from bridge credits and it was paid, or from paid to unpaid, then process refund
    if (
        new_payment_method != bridge_credit_payment_method
        and old_payment_method == bridge_credit_payment_method
        and old_is_paid
    ) or (
        old_payment_method == bridge_credit_payment_method
        and old_is_paid
        and not new_is_paid
    ):

        return handle_bridge_credit_changes_refund(
            club,
            session_entry,
            director,
            old_fee,
            new_fee,
            new_payment_method,
            new_is_paid,
        )

    return "Oops", session_entry


def edit_session_entry_handle_other(
    club,
    session_entry,
    director,
    is_user,
    old_payment_method,
    new_payment_method,
    old_fee,
    new_fee,
    old_is_paid,
    new_is_paid,
):
    """Handle a director making any changes to an entry that don't involve bridge credits or IOUs.

    Returns:
        message(str): message to return to user, can be empty
        session_entry(SessionEntry)
    """

    session_entry.is_paid = new_is_paid
    session_entry.fee = new_fee
    session_entry.payment_method = new_payment_method
    session_entry.save()

    return "Data saved", session_entry


def pay_bridge_credit_for_extra(
    session_misc_payment: SessionMiscPayment,
    session: Session,
    club: Organisation,
    member: User,
):
    """Handle a director paying for an extra from the edit panel using bridge credits

    Returns:
        boolean: Success or Failure

    """

    return payment_api_batch(
        member=member,
        description=f"{session}",
        amount=session_misc_payment.amount,
        organisation=club,
        payment_type="Club Payment",
        session=session,
    )


def refund_bridge_credit_for_extra(
    session_misc_payment: SessionMiscPayment,
    club: Organisation,
    player: User,
    director: User,
):
    """ " Handle an extra with paid bridge credits being changed"""

    update_account(
        member=player,
        amount=session_misc_payment.amount,
        description=f"{BRIDGE_CREDITS} returned for {session_misc_payment.description}",
        payment_type="Refund",
        organisation=club,
    )

    update_organisation(
        organisation=club,
        amount=-session_misc_payment.amount,
        description=f"{BRIDGE_CREDITS} returned for {session_misc_payment.description}",
        payment_type="Refund",
        member=player,
    )

    # log it
    ClubLog(
        organisation=club,
        actor=director,
        action=f"Refunded {player} {GLOBAL_CURRENCY_SYMBOL}{session_misc_payment.amount:.2f} for {session_misc_payment.description}",
    ).save()


def handle_bridge_credit_changes_refund(
    club, session_entry, director, old_fee, new_fee, new_payment_method, new_is_paid
):
    """Handle situation where a refund is required for a session entry"""

    if org_balance(club) < old_fee:
        return "Club has insufficient funds for this refund", session_entry

    player = User.objects.filter(system_number=session_entry.system_number).first()

    update_account(
        member=player,
        amount=old_fee,
        description=f"{BRIDGE_CREDITS} returned for {session_entry.session}",
        payment_type="Refund",
        organisation=club,
    )

    update_organisation(
        organisation=club,
        amount=-old_fee,
        description=f"{BRIDGE_CREDITS} returned for {session_entry.session}",
        payment_type="Refund",
        member=player,
    )

    # log it
    ClubLog(
        organisation=club,
        actor=director,
        action=f"Refunded {player} {GLOBAL_CURRENCY_SYMBOL}{old_fee:.2f} for session",
    ).save()

    # If new payment method is IOU then leave that for the IOU handler to deal with
    if new_payment_method.payment_method != "IOU":
        session_entry.is_paid = new_is_paid
        session_entry.fee = new_fee
        session_entry.payment_method = new_payment_method
        session_entry.save()

    return f"{BRIDGE_CREDITS} refunded to player", session_entry


def session_totals_calculations(
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
            if session_entry.is_paid:
                totals["bridge_credits_received"] += session_entry.fee
        else:
            totals["other_methods_due"] += this_fee
            if session_entry.is_paid:
                totals["other_methods_received"] += session_entry.fee

    totals["tables"] = totals["players"] / 4

    return totals


def handle_change_secondary_payment_method(
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
            handle_iou_changes_on(club, session_entry, administrator)

        if old_method.payment_method == "IOU":
            handle_iou_changes_off(club, session_entry)

    return (
        f". Updated {len(session_entries)} player payment methods."
        if session_entries
        else ". No player payment methods were changed."
    )


def handle_change_additional_session_fee_reason(old_reason, new_reason, session, club):
    """Handle the settings being changed for additional fees - change the reason"""

    session_entries = SessionEntry.objects.filter(session=session).exclude(
        system_number__in=[PLAYING_DIRECTOR, SITOUT]
    )

    for session_entry in session_entries:
        SessionMiscPayment.objects.filter(
            session_entry=session_entry,
            description=old_reason,
        ).update(description=new_reason)


def handle_change_additional_session_fee(old_fee, new_fee, session, club, old_reason):
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


def get_summary_table_data(session, session_entries, mixed_dict, membership_type_dict):
    """Summarise session_entries for the summary view.

    Returns a dictionary like:
        'Bridge Credits':
                            'fee': 150
                            'amount_paid': 90
                            'outstanding': 60
                            'player_count': 5
                            'players': []
                                        User, session_entry, membership
        'Cash': ...

    Note: Users may pay for extras using a different payment method

    We use the fact that SessionEntry and SessionMiscPayment are quite similar.
    """

    # We want the session entry pk to use for both session entries and extras
    for session_entry in session_entries:
        session_entry.session_entry_pk = session_entry.pk
        session_entry.summary_extras = Decimal(0)

    payment_summary = get_summary_table_data_sub(
        {}, session_entries, mixed_dict, membership_type_dict
    )

    extras = SessionMiscPayment.objects.filter(
        session_entry__session=session
    ).select_related("session_entry")

    # extras are really similar to session_entries, make them the same, so we can use the same logic
    for extra in extras:
        extra.is_paid = extra.payment_made
        extra.fee = extra.amount
        extra.system_number = extra.session_entry.system_number
        extra.session_entry_pk = extra.session_entry.pk
        extra.summary_extras = Decimal(0)

    payment_summary = get_summary_table_data_sub(
        payment_summary, extras, mixed_dict, membership_type_dict, extra_flag=True
    )

    return payment_summary


def get_summary_table_data_sub(
    payment_summary, items, mixed_dict, membership_type_dict, extra_flag=False
):
    """sub for get_summary_table_data"""

    for item in items:
        # Skip sitout and director
        if item.system_number in [SITOUT, PLAYING_DIRECTOR]:
            continue

        pay_method = item.payment_method.payment_method

        # Add to dict if not present
        if pay_method not in payment_summary:
            payment_summary[pay_method] = {
                "fee": Decimal(0),
                "extras": Decimal(0),
                "amount_paid": Decimal(0),
                "outstanding": Decimal(0),
                "player_count": 0,
                "players": [],
            }

        # Update dict with this session_entry
        if extra_flag:
            payment_summary[pay_method]["extras"] += item.fee

        payment_summary[pay_method]["fee"] += item.fee

        if item.is_paid:
            payment_summary[pay_method]["amount_paid"] += item.fee
        else:
            payment_summary[pay_method]["outstanding"] += item.fee

        payment_summary[pay_method]["player_count"] += 1

        # Add session_entry as well for drop down list
        name = mixed_dict[item.system_number]["value"]
        member_type = membership_type_dict.get(item.system_number, "Guest")

        # Augment session entry with amount_paid
        item.amount_paid = item.fee if item.is_paid else Decimal(0)

        # Augment session entry with extras - extras is already on the real session entry, but we need our own
        if extra_flag:
            item.summary_extras = item.fee
            item.fee = Decimal(0)

        # Handle visitors
        if item.system_number == VISITOR:
            name = item.player_name_from_file.title()

        new_item = {
            "player": name,
            "session_entry": item,
            "membership": member_type,
        }

        # For extras, we may already have an entry, we want to add to it, not create a new one
        if extra_flag:
            match_flag = False
            for row in payment_summary[pay_method]["players"]:
                if row["player"] == name:
                    match_flag = True
                    row["session_entry"].summary_extras += item.summary_extras
                    if item.is_paid:
                        row["session_entry"].amount_paid += item.amount_paid
                    break
            if not match_flag:
                payment_summary[pay_method]["players"].append(new_item)
        else:
            payment_summary[pay_method]["players"].append(new_item)

    return payment_summary


def get_allowed_payment_methods(session_entries, session, payment_methods):
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
            and session_entry.is_paid
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


def get_table_view_data(session, session_entries):
    """handle formatting for the table view"""

    extras = get_extras_as_total_for_session_entries(session)
    paid_extras = get_extras_as_total_for_session_entries(session, paid_only=True)

    table_list = {}
    table_status = {}
    delete_table_available = {}

    # Give up if no entries
    if not session_entries:
        return table_list, table_status, delete_table_available

    # put session_entries into a dictionary for the table view
    for session_entry in session_entries:

        # Add to dict if not present
        if session_entry.pair_team_number not in table_list:
            table_list[session_entry.pair_team_number] = []
            table_status[session_entry.pair_team_number] = True

        session_entry.extras = Decimal(extras.get(session_entry.id, 0))
        # Add extras to entry fee for this view, no good reason
        session_entry.fee += session_entry.extras

        # Add amount paid
        if session_entry.is_paid:
            session_entry.amount_paid = session_entry.fee
        else:
            session_entry.amount_paid = Decimal(0)

        session_entry.amount_paid += Decimal(paid_extras.get(session_entry.id, 0))

        table_list[session_entry.pair_team_number].append(session_entry)
        if not session_entry.is_paid:
            # unpaid entry, mark table as incomplete
            table_status[session_entry.pair_team_number] = False

    # Add delete option to last table if appropriate

    last_table_session_entries = session_entries.filter(
        pair_team_number=session_entry.pair_team_number
    )
    last_table_paid_entries = last_table_session_entries.filter(is_paid=True).exists()
    last_table_extras = SessionMiscPayment.objects.filter(
        session_entry__in=last_table_session_entries
    ).exists()

    # If there are no paid entries and no paid extras, then the table can be deleted
    if not last_table_paid_entries and not last_table_extras:
        delete_table_available = {session_entry.pair_team_number: True}

    return table_list, table_status, delete_table_available


def process_bridge_credits(session_entries, session, club, bridge_credits, extras):
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

        amount_paid = float(session_entry.fee) if session_entry.is_paid else 0
        fee = float(session_entry.fee) if session_entry.fee else 0
        amount = fee - amount_paid + extras.get(session_entry.id, 0)

        # Try payment
        member = users_by_system_number[session_entry.system_number]
        if payment_api_batch(
            member=member,
            description=f"{session}",
            amount=amount,
            organisation=club,
            payment_type="Club Payment",
            session=session,
        ):
            # Success
            success += 1
            session_entry.is_paid = True
            session_entry.save()

            # mark any misc payments for this session as paid
            SessionMiscPayment.objects.filter(
                session_entry__session=session,
                session_entry__system_number=session_entry.system_number,
            ).update(payment_made=True, payment_method=bridge_credits)

        else:
            # Payment failed - change payment method and fees
            failures.append(member)
            session_entry.payment_method = session.default_secondary_payment_method
            session_entry.fee = get_session_fee_for_player(session_entry, club)
            session_entry.save()

    # Update status of session - see if there are any payments left
    recalculate_session_status(session)

    return success, failures


def add_table(session):
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
        ).save()


def delete_table(session, table_number):
    """delete a table"""

    last_table_session_entries = SessionEntry.objects.filter(
        session=session, pair_team_number=table_number
    )
    last_table_paid_entries = last_table_session_entries.filter(is_paid=True).exists()
    last_table_extras = SessionMiscPayment.objects.filter(
        session_entry__in=last_table_session_entries
    ).exists()

    # If there are no paid entries and no paid extras, then the table can be deleted
    if not last_table_paid_entries and not last_table_extras:
        last_table_session_entries.delete()
        return True

    return False


def recalculate_session_status(session: Session):
    """recalculate what state a session is in based upon the payment status of its session entries"""

    # Are there still outstanding payments?
    if (
        not SessionEntry.objects.filter(session=session, is_paid=False).exists()
        and not SessionMiscPayment.objects.filter(
            session_entry__session=session, payment_made=False
        ).exists()
    ):
        session.status = Session.SessionStatus.COMPLETE

    # Are there outstanding bridge credits?
    elif (
        not SessionEntry.objects.filter(
            session=session,
            is_paid=False,
            payment_method__payment_method="Bridge Credits",
        ).exists()
        and not SessionMiscPayment.objects.filter(
            session_entry__session=session,
            payment_made=False,
            payment_method__payment_method="Bridge Credits",
        ).exists()
    ):
        session.status = Session.SessionStatus.CREDITS_PROCESSED

    else:
        session.status = Session.SessionStatus.DATA_LOADED

    session.save()


def reset_values_on_session_entry(session_entry: SessionEntry, club: Organisation):
    """Reset common fields when a user is changed"""

    # return values to defaults
    session_entry.is_paid = False
    session_entry.fee = get_session_fee_for_player(session_entry, club)

    # TODO: Decide if we should do this or not
    # Mark extras as unpaid - we can't get here with paid extras for Bridge Credits or IOUs
    # SessionMiscPayment.objects.filter(session_entry=session_entry).update(payment_made=False)

    return session_entry


def change_user_on_session_entry(
    club: Organisation,
    session_entry: SessionEntry,
    source,
    system_number,
    sitout,
    playing_director,
    non_abf_visitor,
    member_last_name_search,
    member_first_name_search,
    director,
):
    """Handle changing the player on a session entry

    We could get:

    source and system number for a User or UnregisteredUser
    sitout - change to a sitout
    playing_director - change to a playing director
    non_abf_visitor - someone who isn't registered with the ABF, also get the first and last name

    If Bridge Credits or IOUs are in place, we reject the change

    """

    if session_entry.payment_method:

        # Check for bridge credits already paid
        if (
            session_entry.payment_method.payment_method == "Bridge Credits"
            and session_entry.is_paid
        ):
            return f"{BRIDGE_CREDITS} have been paid for this entry. You need to refund them before you can change the player."

        # Check for IOUs already paid
        if (
            session_entry.payment_method.payment_method == "IOU"
            and session_entry.is_paid
        ):
            return "IOUs have been paid for this entry. You need to reverse them before you can change the player."

    # Check for paid extras
    bad_extras = (
        SessionMiscPayment.objects.filter(session_entry=session_entry)
        .filter(payment_made=True)
        .filter(payment_method__payment_method__in=["Bridge Credits", "IOU"])
        .exists()
    )
    if bad_extras:
        return "Extras have been paid for this entry which need to be reversed before changing the player."

    # Non-paying people
    if sitout:
        return change_user_on_session_entry_non_player(
            SITOUT, session_entry, club, "Player changed to Sit Out"
        )

    if playing_director:
        return change_user_on_session_entry_non_player(
            PLAYING_DIRECTOR, session_entry, club, "Player changed to Playing Director"
        )

    # Non-ABF visitor
    if non_abf_visitor:
        session_entry.system_number = VISITOR
        session_entry = reset_values_on_session_entry(session_entry, club)
        session_entry.player_name_from_file = (
            f"{member_first_name_search} {member_last_name_search}"
        )
        session_entry.save()
        return f"Player changed to a visitor with no {GLOBAL_ORG} number"

    # Registered or Unregistered User
    if system_number:

        if source == "mpc":
            # We don't know about this user, so add them. We don't add an email address though

            # lookup name from system_number
            mp_source = masterpoint_factory_creator()
            status, return_value = mp_source.system_number_lookup_api(system_number)

            if not status:
                return f"Error looking up {GLOBAL_ORG} Number: {system_number}"

            UnregisteredUser(
                system_number=system_number,
                last_updated_by=director,
                last_name=return_value[1],
                first_name=return_value[0],
                origin="Manual",
                added_by_club=club,
            ).save()
            ClubLog(
                organisation=club,
                actor=director,
                action=f"Added un-registered user {return_value[0]} {return_value[1]}",
            ).save()

        return change_user_on_session_entry_non_player(
            system_number, session_entry, club, "Player changed"
        )

    return "Error Occurred. Should not reach here."


def change_user_on_session_entry_non_player(player_type, session_entry, club, message):
    """sub of change_user_on_session_entry"""

    session_entry.system_number = player_type
    session_entry = reset_values_on_session_entry(session_entry, club)
    session_entry.save()
    return message
