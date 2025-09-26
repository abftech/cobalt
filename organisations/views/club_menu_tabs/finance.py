import datetime

import pytz
from django.db.models import Sum, Min
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from club_sessions.models import Session
from cobalt.settings import GLOBAL_CURRENCY_SYMBOL, BRIDGE_CREDITS, TIME_ZONE
from events.models import Event, Congress
from notifications.views.core import send_cobalt_email_to_system_number
from organisations.decorators import check_club_menu_access
from organisations.models import ClubLog, MemberMembershipType, Organisation
from organisations.views.club_menu import tab_finance_htmx
from organisations.views.club_menu_tabs.members import club_admin_edit_member_htmx
from organisations.club_admin_core import (
    is_member_allowing_auto_pay,
    is_player_a_member,
)
from payments.models import (
    UserPendingPayment,
    OrganisationTransaction,
    TRANSACTION_TYPE,
)
from payments.views.admin import settlement
from payments.views.core import (
    update_account,
    update_organisation,
    org_balance,
    org_balance_at_date,
)
from payments.views.org_report.csv import organisation_transactions_csv_download
from payments.views.org_report.data import (
    organisation_transactions_by_date_range,
    sessions_and_payments_by_date_range,
    event_payments_summary_by_date_range,
    combined_view_events_sessions_other,
    congress_payments_summary_by_date_range,
)
from payments.views.org_report.xls import organisation_transactions_xls_download
from payments.views.payments_api import payment_api_batch
from rbac.core import (
    rbac_get_users_in_group_by_name,
)
from utils.utils import cobalt_paginator


@check_club_menu_access(check_payments=True)
def cancel_user_pending_debt_htmx(request, club):
    """Cancel a debt for a user"""

    user_pending_payment = get_object_or_404(
        UserPendingPayment, pk=request.POST.get("user_pending_payment_id")
    )
    if user_pending_payment.organisation != club:
        message = "This debt is not for this club"
    else:
        user_pending_payment.delete()
        message = "Pending payment deleted"

        ClubLog(
            organisation=club,
            actor=request.user,
            action=f"Cancelled debt for {user_pending_payment.system_number} for {GLOBAL_CURRENCY_SYMBOL}{user_pending_payment.amount:.2f}",
        ).save()

    # We get called from the member page too, check if we should return the member view or default ot finance
    if request.POST.get("return_member_tab"):
        # JPG cleanup
        # return edit_member_htmx(request, message=message)
        request.POST = request.POST.copy()
        request.POST["system_number"] = user_pending_payment.system_number
        request.POST["message"] = message
        return club_admin_edit_member_htmx(request)

    return tab_finance_htmx(request, message=message)


@check_club_menu_access(check_payments=True)
def get_org_balance_htmx(request, club):
    """Show balance for this club"""

    last_tran = OrganisationTransaction.objects.filter(organisation=club).last()
    balance = last_tran.balance if last_tran else 0.0

    return HttpResponse(f"${balance:,.2f}")


@check_club_menu_access(check_payments_view=True)
def transactions_htmx(request, club):
    """handle the transaction listing part of the finance tab"""

    # Get view type - default to all
    view_type = request.POST.get("view_type", "all")

    if view_type == "session":
        things = _summary_by_sessions(request, club)

    elif view_type == "event":
        things = _summary_by_events(request, club)

    elif view_type == "other":
        transactions = (
            OrganisationTransaction.objects.filter(organisation=club)
            .filter(event_id__isnull=True)
            .filter(club_session_id__isnull=True)
            .order_by("-pk")
        )
        things = cobalt_paginator(request, transactions)

    elif view_type == "membership":
        transactions = OrganisationTransaction.objects.filter(
            organisation=club,
            type="Club Membership",
        ).order_by("-pk")
        things = cobalt_paginator(request, transactions)

    else:  # all
        transactions = OrganisationTransaction.objects.filter(
            organisation=club
        ).order_by("-pk")
        things = cobalt_paginator(request, transactions)

    hx_post = reverse("organisations:transactions_htmx")
    hx_target = "#id_finance_transactions"
    hx_vars = f"club_id: {club.id}, view_type: '{view_type}'"

    return render(
        request,
        "organisations/club_menu/finance/transactions_htmx.html",
        {
            "club": club,
            "things": things,
            "hx_post": hx_post,
            "hx_target": hx_target,
            "hx_vars": hx_vars,
            "view_type": view_type,
        },
    )


def _summary_by_sessions(request, club):
    """Summarise by session only"""

    # Get the session transactions on their own and paginate
    session_transactions = (
        OrganisationTransaction.objects.filter(organisation=club)
        .exclude(club_session_id=None)
        .order_by("-club_session_id")
        .values("description", "club_session_id")
        .annotate(amount=Sum("amount"))
        .annotate(created_date=Min("created_date"))
    )

    return cobalt_paginator(request, session_transactions)


def _summary_by_events(request, club):
    """Summarise by event only"""

    # TODO: This loads all events for an organisation since the start of time. Probably okay for many years, but
    # may need fixed later.

    # Get the event transactions on their own and paginate
    event_transactions = (
        OrganisationTransaction.objects.filter(organisation=club)
        .exclude(event_id=None)
        .order_by("-event_id")
        .values("event_id")
        .annotate(amount=Sum("amount"))
        .annotate(created_date=Min("created_date"))
    )

    # Get event names
    event_ids = event_transactions.values_list("event_id")
    event_names = Event.objects.filter(id__in=event_ids).values(
        "id", "congress__name", "event_name"
    )

    event_names_dict = {}
    for event_name in event_names:
        event_names_dict[event_name["id"]] = (
            f"{event_name['congress__name']} - {event_name['event_name']}"
        )

    # Augment data
    for event_transaction in event_transactions:
        event_transaction["description"] = event_names_dict[
            event_transaction["event_id"]
        ]

    return cobalt_paginator(request, event_transactions)


def pay_member_from_organisation(
    request,
    club,
    amount,
    description,
    member,
    event_id=-1,
    session_id=-1,
    is_membership_fee=False,
):
    """Pay a member from an organisation's account. Calling module is responsible for security.

    This works off the request object.

    Request should have member_id, description and amount. Although description can be overridden as a parameter

    Return: status, message

    Status is True/False for success
    Message contains tet narrative

    """

    if amount <= 0:
        return False, "Amount was less than zero"

    if amount > org_balance(club):
        return False, "Club has insufficient funds for this transfer"

    event = Event.objects.get(pk=event_id) if event_id > 0 else None
    session = Session.objects.get(pk=session_id) if session_id > 0 else None

    # Pay user
    update_account(
        member=member,
        amount=amount,
        description=description,
        organisation=club,
        payment_type="Org Transfer" if not is_membership_fee else "Club Membership",
    )

    # debit club
    update_organisation(
        organisation=club,
        amount=-amount,
        description=description,
        payment_type="Org Transfer" if not is_membership_fee else "Club Membership",
        member=member,
        event=event,
        session=session,
    )

    # log it
    ClubLog(
        organisation=club,
        actor=request.user,
        action=f"Paid {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} to {member}",
    ).save()

    # notify user
    # COB-768 JPG 15-12-23: Change in message text
    msg = f"""{club} (administrator {request.user}) has paid {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} to your {BRIDGE_CREDITS}
    account for {description}.
        <br><br>If you have any queries please contact {club} in the first instance.
    """
    send_cobalt_email_to_system_number(
        system_number=member.system_number,
        subject=f"Payment from {club}",
        message=msg,
        club=club,
    )

    return (
        True,
        f"Payment of {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} made to {member.full_name}",
    )


def top_up_member_from_organisation(request, club, amount, description, member):
    """Pay a member from an organisation's account when a top up is made. Calling module is responsible for security.

    This works off the request object.

    Request should have member_id, description and amount. Although description can be overridden as a parameter

    Return: status, message

    Status is True/False for success
    Message contains tet narrative

    """

    if amount <= 0:
        return False, "Amount was less than zero"

    if amount > org_balance(club):
        return False, "Club has insufficient funds for this transfer"

    # Pay user
    update_account(
        member=member,
        amount=amount,
        description=description,
        organisation=club,
        payment_type="Club Top Up",
    )

    # debit club
    update_organisation(
        organisation=club,
        amount=-amount,
        description=description,
        payment_type="Club Top Up",
        member=member,
    )

    # log it
    ClubLog(
        organisation=club,
        actor=request.user,
        action=f"Made top up payment of {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} to {member}",
    ).save()

    return (
        True,
        f"Top Up of {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} made to {member.full_name}",
    )


@check_club_menu_access(check_payments=True)
def pay_member_htmx(request, club):
    """make a payment to a member"""

    if "save" not in request.POST:
        hx_post = reverse("organisations:pay_member_htmx")
        events = (
            Event.objects.filter(congress__congress_master__org=club)
            .select_related("congress")
            .order_by("-denormalised_start_date")[:20]
        )
        sessions = Session.objects.filter(session_type__organisation=club).order_by(
            "-session_date"
        )[:20]
        return render(
            request,
            "organisations/club_menu/finance/pay_member_htmx.html",
            {"club": club, "hx_post": hx_post, "events": events, "sessions": sessions},
        )

    member = get_object_or_404(User, pk=request.POST.get("member_id"))
    amount = float(request.POST.get("amount"))
    description = request.POST.get("description")
    event_id = int(request.POST.get("event_id", -1))
    session_id = int(request.POST.get("session_id", -1))
    is_membership_fee = request.POST.get("membership_fee", False)

    _, message = pay_member_from_organisation(
        request,
        club,
        amount,
        description,
        member,
        event_id,
        session_id,
        is_membership_fee,
    )

    return tab_finance_htmx(request, message=message)


@check_club_menu_access(check_payments=True)
def charge_member_htmx(request, club):
    """make a charge to a member"""

    if "save" not in request.POST:
        hx_post = reverse("organisations:charge_member_htmx")
        return render(
            request,
            "organisations/club_menu/finance/charge_member_htmx.html",
            {"club": club, "hx_post": hx_post},
        )

    member = get_object_or_404(User, pk=request.POST.get("member_id"))
    description = request.POST.get("description")
    amount = float(request.POST.get("amount"))
    is_membership_fee = request.POST.get("membership_fee", False)

    # Validate
    if amount <= 0:
        return tab_finance_htmx(request, message="Amount was less than zero")

    # Check membership
    # JPG Query - this will just check for current active members.
    if not is_player_a_member(club, member.system_number):
        return tab_finance_htmx(
            request,
            message=f"{member} is not a member of the club. Cannot charge user.",
        )

    if is_membership_fee:
        if not is_member_allowing_auto_pay(club=club, user=member):
            return tab_finance_htmx(
                request,
                message=(
                    f"{member} is not allowing the club to charge their membership fees "
                    + f"to {BRIDGE_CREDITS}."
                ),
            )

    # Try to charge user
    if payment_api_batch(
        member=member,
        amount=amount,
        description=description,
        organisation=club,
        payment_type="Org Transfer" if not is_membership_fee else "Club Membership",
    ):

        # log it
        ClubLog(
            organisation=club,
            actor=request.user,
            action=f"Charged {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} to {member}",
        ).save()

        # notify user
        # COB-768 JPG 15-12-23: Change in message text
        msg = f"""{club} (administrator {request.user}) has charged {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} to your {BRIDGE_CREDITS}
        account for {description}.
            <br><br>If you have any queries please contact {club} in the first instance.
        """
        send_cobalt_email_to_system_number(
            system_number=member.system_number,
            subject=f"Charge from {club}",
            message=msg,
            club=club,
        )

        return tab_finance_htmx(
            request,
            message=f"Charge of {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} made to {member.full_name} via {BRIDGE_CREDITS}",
        )

    else:

        return tab_finance_htmx(
            request,
            message=f"Payment FAILED for {member.full_name}. Insufficient funds.",
        )


@check_club_menu_access(check_payments=True)
def pay_org_htmx(request, club):
    """make a payment to another club"""

    if "save" not in request.POST:
        return render(
            request,
            "organisations/club_menu/finance/pay_org_htmx.html",
            {"club": club},
        )

    org = get_object_or_404(Organisation, pk=request.POST.get("org_id"))
    description = request.POST.get("description")
    amount = float(request.POST.get("amount"))

    # Validate
    if amount <= 0:
        return tab_finance_htmx(request, message="Amount was less than zero")

    if amount > org_balance(club):
        return tab_finance_htmx(
            request, message="Club has insufficient funds for this transfer"
        )

    if org == club:
        return tab_finance_htmx(
            request, message="Ignoring attempt to transfer to yourself"
        )

    # debit this club
    update_organisation(
        organisation=club,
        amount=-amount,
        description=description,
        payment_type="Org Transfer",
        other_organisation=org,
    )

    # credit other club
    update_organisation(
        organisation=org,
        amount=amount,
        description=description,
        payment_type="Org Transfer",
        other_organisation=club,
    )

    # log it
    ClubLog(
        organisation=club,
        actor=request.user,
        action=f"Transferred {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} to {org}",
    ).save()

    # notify payments users at other club, not general admins though
    # There is no really clean way to do this. We use the rbac tree to find either the basic group (basic RBAC) or
    # the payments_edit group (advanced RBAC).

    # try basic
    other_club_admins = rbac_get_users_in_group_by_name(
        f"{club.rbac_name_qualifier}.basic"
    )

    if not other_club_admins:
        # try advanced
        other_club_admins = rbac_get_users_in_group_by_name(
            f"{club.rbac_name_qualifier}.payments_edit"
        )

    for other_club_admin in other_club_admins:
        msg = f"""{request.user} from {club} has paid {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} into the {BRIDGE_CREDITS}
        account for {org}. The description was: {description}.
            <br><br>If you have any queries please contact {club} in the first instance.
        """
        send_cobalt_email_to_system_number(
            system_number=other_club_admin.system_number,
            subject=f"Transfer from {club}",
            message=msg,
            club=club,
        )

    return tab_finance_htmx(
        request,
        message=f"Transfer of {GLOBAL_CURRENCY_SYMBOL}{amount:,.2f} made to {org} via {BRIDGE_CREDITS}",
    )


@check_club_menu_access(check_payments=True)
def transaction_details_htmx(request, club):
    """return details of a transaction"""

    trans = get_object_or_404(OrganisationTransaction, pk=request.POST.get("trans_id"))
    if trans.organisation != club:
        return HttpResponse("Transaction does not belong to this club")

    return render(
        request,
        "organisations/club_menu/finance/transaction_detail_htmx.html",
        {"club": club, "trans": trans},
    )


@check_club_menu_access(check_payments=True)
def transaction_event_details_htmx(request, club):
    """return a breakdown of the transactions that make up payments for an event. Appears on the finance view when
    a user drills into the event"""

    use_filtered_view = request.POST.get("use_filtered_view")

    # Get transactions and paginate
    event = get_object_or_404(Event, pk=request.POST.get("event_id"))
    event_transactions = OrganisationTransaction.objects.filter(
        organisation=club, event_id=event.id
    ).order_by("-created_date")
    things = cobalt_paginator(request, event_transactions)

    # Set up HTMX data

    hx_post = reverse("organisations:transaction_event_details_htmx")
    hx_vars = f"club_id: {club.id}, event_id:{event.id}"

    if use_filtered_view:
        hx_target = "#id_filtered_transactions"
        hx_vars = f"{hx_vars}, use_filtered_view:1"
    else:
        hx_target = "#id_finance_transactions"

    return render(
        request,
        "organisations/club_menu/finance/transaction_event_detail_htmx.html",
        {
            "things": things,
            "club": club,
            "event": event,
            "use_filtered_view": use_filtered_view,
            "hx_post": hx_post,
            "hx_target": hx_target,
            "hx_vars": hx_vars,
        },
    )


@check_club_menu_access(check_payments=True)
def transaction_congress_details_htmx(request, club):
    """return a list of events for a congress so the user can drill into the details"""

    use_filtered_view = request.POST.get("use_filtered_view")

    # Get congress from POST
    congress_id = request.POST.get("congress_id")
    congress = get_object_or_404(Congress, pk=congress_id)

    # Get events for this congress
    event_ids = Event.objects.filter(congress_id=congress_id)

    # Get payments for these events
    event_payments = (
        OrganisationTransaction.objects.filter(organisation=club)
        .filter(event_id__in=event_ids)
        .values("event_id")
        .annotate(amount=Sum("amount"))
    )

    # Turn into dictionary
    event_payments_dict = {}
    for event_payment in event_payments:
        event_payments_dict[event_payment["event_id"]] = event_payment["amount"]

    # Get events so we have name, dates etc
    events = Event.objects.filter(pk__in=event_ids).order_by("-denormalised_start_date")

    # Augment with payment amounts
    for event in events:
        event.total_payments = event_payments_dict.get(event.id, 0)

    things = cobalt_paginator(request, events)

    # Set up HTMX data

    hx_post = reverse("organisations:transaction_congress_details_htmx")
    hx_vars = f"club_id: {club.id}, congress_id:{congress.id}"

    if use_filtered_view:
        hx_target = "#id_filtered_transactions"
        hx_vars = f"{hx_vars}, use_filtered_view:1"
    else:
        hx_target = "#id_finance_transactions"

    return render(
        request,
        "organisations/club_menu/finance/transaction_congress_detail_htmx.html",
        {
            "things": things,
            "club": club,
            "congress": congress,
            "use_filtered_view": use_filtered_view,
            "hx_post": hx_post,
            "hx_target": hx_target,
            "hx_vars": hx_vars,
        },
    )


@check_club_menu_access(check_payments=True)
def transaction_session_details_htmx(request, club):
    """return details of a session"""

    club_session = get_object_or_404(Session, pk=request.POST.get("club_session_id"))
    session_transactions = OrganisationTransaction.objects.filter(
        organisation=club, club_session_id=club_session.id
    )
    # trans = get_object_or_404(OrganisationTransaction, pk=request.POST.get("trans_id"))
    # if trans.organisation != club:
    #     return HttpResponse("Transaction does not belong to this club")

    return render(
        request,
        "organisations/club_menu/finance/transaction_session_detail_htmx.html",
        {
            "club": club,
            "club_session": club_session,
            "session_transactions": session_transactions,
        },
    )


@check_club_menu_access(check_payments=True)
def transaction_filter_htmx(request, club):
    """tab for CSV downloads and filtered view"""

    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    description_search = request.POST.get("description_search")
    view_type_selector = request.POST.get("view_type_selector")
    transaction_type = request.POST.get("transaction_type_selector")

    if not view_type_selector:
        # first call - show blank form

        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        last_month = today.replace(day=1) - datetime.timedelta(days=1)
        first_of_last_month_str = f"{last_month.strftime('%Y-%m')}-01"
        last_of_last_month_str = last_month.strftime("%Y-%m-%d")
        first_of_last_year_str = datetime.date(
            int(today.strftime("%Y")) - 1, 1, 1
        ).strftime("%Y-%m-%d")
        last_of_last_year_str = datetime.date(
            int(today.strftime("%Y")) - 1, 12, 31
        ).strftime("%Y-%m-%d")

        reference_dates = {
            "Month to date": (
                f"{datetime.date.today().strftime('%Y-%m')}-01",
                today_str,
            ),
            "Year to date": (
                f"{datetime.date.today().strftime('%Y')}-01-01",
                today_str,
            ),
            "Last Month": (first_of_last_month_str, last_of_last_month_str),
            "Last Year": (first_of_last_year_str, last_of_last_year_str),
            "All": ("1901-01-01", today_str),
        }

        return render(
            request,
            "organisations/club_menu/finance/transaction_filter_htmx.html",
            {
                "club": club,
                "reference_dates": reference_dates,
                "transaction_type": "all",
                "transaction_types": TRANSACTION_TYPE,
            },
        )

    if not start_date or not end_date:
        return HttpResponse("Enter dates to perform search")

    if "download-csv" in request.POST:
        return organisation_transactions_csv_download(
            request,
            club,
            start_date,
            end_date,
            description_search,
            transaction_type,
        )

    if "download-xls" in request.POST:
        return organisation_transactions_xls_download(
            request, club, start_date, end_date, description_search
        )

    if "show_filtered_data" in request.POST:
        return organisation_transactions_filtered_data(
            request,
            club,
            start_date,
            end_date,
            description_search,
            view_type_selector,
            transaction_type,
        )

    return HttpResponse("an error occurred")


def organisation_transactions_filtered_data(
    request,
    club,
    start_date,
    end_date,
    description_search,
    view_type_selector,
    transaction_type,
):
    """show filtered data (date and search) on screen, not as CSV/XLS download"""

    # set up data for pagination footer
    hx_data = {
        "hx_post": reverse("organisations:transaction_filter_htmx"),
        "hx_vars": f"club_id: {club.id}, show_filtered_data: 1, start_date: '{start_date}', end_date: '{end_date}', view_type_selector: '{view_type_selector}', transaction_type_selector: '{transaction_type}'",
    }

    # The movement report uses its own hx-target so allow this to be overridden
    hx_target = request.POST.get("hx_target", "#id_filtered_transactions")
    hx_data["hx_target"] = hx_target
    hx_data["hx_vars"] = f"{hx_data['hx_vars']}, hx_target: '{hx_target}'"

    if description_search:
        hx_data["hx_vars"] = (
            f"{hx_data['hx_vars']}, description_search: '{description_search}'"
        )

    if view_type_selector == "all" or (
        view_type_selector == "txntype" and transaction_type == "all"
    ):
        return organisation_transactions_filtered_data_all(
            request, club, start_date, end_date, description_search, hx_data
        )

    elif view_type_selector == "session":
        return organisation_transactions_filtered_data_sessions(
            request, club, start_date, end_date, hx_data
        )

    elif view_type_selector == "event":
        return organisation_transactions_filtered_data_events(
            request, club, start_date, end_date, hx_data
        )

    elif view_type_selector == "congress":
        return organisation_transactions_filtered_data_congresses(
            request, club, start_date, end_date, hx_data
        )

    elif view_type_selector == "combined":
        return organisation_transactions_filtered_data_combined(
            request, club, start_date, end_date, hx_data
        )

    elif view_type_selector == "txntype":
        return organisation_transactions_filtered_data_txntype(
            request,
            club,
            start_date,
            end_date,
            description_search,
            hx_data,
            transaction_type,
        )

    elif view_type_selector == "movement":
        return organisation_transactions_filtered_data_movement(
            request,
            club,
            start_date,
            end_date,
            hx_data,
        )

    else:
        return HttpResponse("No view provided")


def organisation_transactions_filtered_data_txntype(
    request,
    club,
    start_date,
    end_date,
    description_search,
    hx_data,
    transaction_type,
):
    """handle the filter by transaction type option"""

    organisation_transactions = organisation_transactions_by_date_range(
        club,
        start_date,
        end_date,
        description_search,
        augment_data=False,
        transaction_type=transaction_type,
    )

    total_for_type = 0
    for org_transaction in organisation_transactions:
        total_for_type += org_transaction.amount

    things = cobalt_paginator(request, organisation_transactions, 50)

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_txntype_htmx.html",
        {
            "club": club,
            "things": things,
            "organisation_transactions": organisation_transactions,
            "total_for_type": total_for_type,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )


def organisation_transactions_filtered_data_movement(
    request,
    club,
    start_date,
    end_date,
    hx_data,
):
    """handle the filter by movement option"""

    # Dates
    end_datetime_raw = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    end_datetime_raw += datetime.timedelta(days=1)
    end_datetime = timezone.make_aware(end_datetime_raw, pytz.timezone(TIME_ZONE))
    start_datetime_raw = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    start_datetime = timezone.make_aware(start_datetime_raw, pytz.timezone(TIME_ZONE))

    # Queries
    opening_balance = org_balance_at_date(club, start_date, start_of_day_balance=True)
    closing_balance = org_balance_at_date(club, end_date)
    base_query = (
        OrganisationTransaction.objects.filter(organisation=club)
        .filter(created_date__gte=start_datetime)
        .filter(created_date__lt=end_datetime)
    )
    settlements = base_query.filter(type="Settlement").aggregate(total=Sum("amount"))
    event_entries = base_query.filter(type="Entry to an event").aggregate(
        total=Sum("amount")
    )
    club_sessions = base_query.filter(type="Club Payment").aggregate(
        total=Sum("amount")
    )
    club_memberships = base_query.filter(type="Club Membership").aggregate(
        total=Sum("amount")
    )
    other_adjustments = (
        base_query.exclude(
            type__in=[
                "Settlement",
                "Entry to an event",
                "Club Payment",
                "Club Membership",
            ]
        )
        .exclude(event_id__isnull=False)
        .aggregate(total=Sum("amount"))
    )

    # Reformat date strings to be consistent
    start_date_display = f"{start_date[8:10]}/{start_date[5:7]}/{start_date[:4]}"
    end_date_display = f"{end_date[8:10]}/{end_date[5:7]}/{end_date[:4]}"

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_movement_htmx.html",
        {
            "club": club,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "settlements": settlements["total"] or 0,
            "event_entries": event_entries["total"] or 0,
            "club_sessions": club_sessions["total"] or 0,
            "club_memberships": club_memberships["total"] or 0,
            "other_adjustments": other_adjustments["total"] or 0,
            "start_date": start_date,
            "start_date_display": start_date_display,
            "end_date": end_date,
            "end_date_display": end_date_display,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )


def organisation_transactions_filtered_data_all(
    request, club, start_date, end_date, description_search, hx_data
):
    """handle the all option"""

    organisation_transactions = organisation_transactions_by_date_range(
        club, start_date, end_date, description_search, augment_data=False
    )

    things = cobalt_paginator(request, organisation_transactions, 50)

    balance_at_end_date = org_balance_at_date(club, end_date)
    end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_all_htmx.html",
        {
            "club": club,
            "things": things,
            "balance_at_end_date": balance_at_end_date,
            "end_datetime": end_datetime,
            "organisation_transactions": organisation_transactions,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )


def organisation_transactions_filtered_data_sessions(
    request, club, start_date, end_date, hx_data
):
    """handle the sessions option"""

    # Get data
    sessions_in_range, payments_dict = sessions_and_payments_by_date_range(
        club, start_date, end_date
    )

    # Add session total amount to data
    sessions_total = 0
    for session_in_range_id in sessions_in_range:
        sessions_in_range[session_in_range_id].amount = payments_dict.get(
            session_in_range_id, "No Payments"
        )
        # COB-772
        sessions_total += payments_dict.get(session_in_range_id, 0)

    # Paginate
    list_of_sessions = list(sessions_in_range.values())
    list_of_sessions.reverse()
    things = cobalt_paginator(request, list_of_sessions)

    balance_at_end_date = org_balance_at_date(club, end_date)
    end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_sessions_htmx.html",
        {
            "club": club,
            "things": things,
            "balance_at_end_date": balance_at_end_date,
            "end_datetime": end_datetime,
            "sessions_total": sessions_total,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )


def organisation_transactions_filtered_data_events(
    request, club, start_date, end_date, hx_data
):
    """handle the events option"""

    event_data = event_payments_summary_by_date_range(club, start_date, end_date)

    list_of_events = list(event_data.values())
    list_of_events.reverse()
    things = cobalt_paginator(request, list_of_events)

    # COB-772
    balance_at_end_date = org_balance_at_date(club, end_date)
    end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    events_total = 0
    for event_id in event_data:
        events_total += event_data[event_id]["amount"]

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_events_htmx.html",
        {
            "club": club,
            "things": things,
            "balance_at_end_date": balance_at_end_date,
            "end_datetime": end_datetime,
            "events_total": events_total,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )


def organisation_transactions_filtered_data_combined(
    request, club, start_date, end_date, hx_data
):
    """handle the all option"""

    organisation_transactions = combined_view_events_sessions_other(
        club, start_date, end_date
    )

    # this is a tuple, convert to a list
    data = [
        organisation_transaction[1]
        for organisation_transaction in organisation_transactions
    ]
    data.reverse()
    things = cobalt_paginator(request, data)

    # COB-772
    balance_at_end_date = org_balance_at_date(club, end_date)
    end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_combined_htmx.html",
        {
            "club": club,
            "things": things,
            "balance_at_end_date": balance_at_end_date,
            "end_datetime": end_datetime,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )


def organisation_transactions_filtered_data_congresses(
    request, club, start_date, end_date, hx_data
):
    """handle the congress option"""

    congress_data = congress_payments_summary_by_date_range(club, start_date, end_date)
    print(congress_data)

    list_of_congresses = list(congress_data.values())
    list_of_congresses.reverse()
    things = cobalt_paginator(request, list_of_congresses)

    # COB-772
    balance_at_end_date = org_balance_at_date(club, end_date)
    end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    congresses_total = 0
    for congress_id in congress_data:
        congresses_total += congress_data[congress_id]["amount"]

    return render(
        request,
        "organisations/club_menu/finance/organisation_transactions_filtered_data_congresses_htmx.html",
        {
            "club": club,
            "things": things,
            "balance_at_end_date": balance_at_end_date,
            "end_datetime": end_datetime,
            "congresses_total": congresses_total,
            "hx_target": hx_data["hx_target"],
            "hx_post": hx_data["hx_post"],
            "hx_vars": hx_data["hx_vars"],
        },
    )
