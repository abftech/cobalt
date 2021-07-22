# -*- coding: utf-8 -*-
"""Handles all activities associated with payments that talk to users.

This module handles all of the functions that interact directly with
a user. i.e. they generally accept a ``Request`` and return an
``HttpResponse``.
See also `Payments Core`_. This handles the other side of the interactions.
They both work together.

Key Points:
    - Payments is a service module, it is requested to do things on behalf of
      another module and does not know why it is doing them.
    - Payments are often not real time, for manual payments, the user will
      be taken to another screen that interacts directly with Stripe, and for
      automatic top up payments, the top up may fail and require user input.
    - The asynchronous nature of payments makes it more complex than many of
      the Cobalt modules so the documentation needs to be of a higher standard.
      See `Payments Overview`_ for more details.

.. _Payments Core:
   #module-payments.core

.. _Payments Overview:
   ./payments_overview.html

"""

import csv
import datetime
from itertools import chain

import requests
import stripe
import pytz
from django.db.transaction import atomic
from django.utils import timezone, dateformat
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from django.db import transaction
from django.contrib import messages
from datetime import timedelta

from masterpoints.views import user_summary
from notifications.views import contact_member
from logs.views import log_event
from cobalt.settings import (
    STRIPE_SECRET_KEY,
    GLOBAL_MPSERVER,
    AUTO_TOP_UP_MAX_AMT,
    AUTO_TOP_UP_DEFAULT_AMT,
    GLOBAL_ORG,
    GLOBAL_ORG_ID,
    GLOBAL_CURRENCY_SYMBOL,
    BRIDGE_CREDITS,
    TIME_ZONE,
    COBALT_HOSTNAME,
)
from .forms import (
    MemberTransfer,
    MemberTransferOrg,
    ManualTopup,
    SettlementForm,
    AdjustMemberForm,
    AdjustOrgForm,
    DateForm,
    PaymentStaticForm,
    OrgStaticOverrideForm,
    StripeRefund,
)
from .core import (
    payment_api,
    get_balance,
    auto_topup_member,
    update_organisation,
    update_account,
    stripe_current_balance,
)
from organisations.views import org_balance
from .models import (
    MemberTransaction,
    StripeTransaction,
    OrganisationTransaction,
    PaymentStatic,
    OrganisationSettlementFees,
)
from accounts.models import User, TeamMate
from utils.utils import cobalt_paginator
from organisations.models import Organisation
from rbac.core import rbac_user_has_role
from rbac.views import rbac_forbidden
from rbac.decorators import rbac_check_role
from django.utils.timezone import make_aware

TZ = pytz.timezone(TIME_ZONE)


####################
# statement_common #
####################
def statement_common(user):
    """Member statement view - common part across online, pdf and csv

    Handles the non-formatting parts of statements.

    Args:
        user (User): standard user object

    Returns:
        5-element tuple containing
            - **summary** (*dict*): Basic info about user from MasterPoints
            - **club** (*str*): Home club name
            - **balance** (*float* or *str*): Users account balance
            - **auto_button** (*bool*): status of auto top up
            - **events_list** (*list*): list of MemberTransactions

    """

    # Get summary data
    qry = "%s/mps/%s" % (GLOBAL_MPSERVER, user.system_number)
    try:
        summary = requests.get(qry).json()[0]
    except IndexError:  # server down or some error
        # raise Http404
        summary = {"IsActive": False, "HomeClubID": 0}

    # Set active to a boolean
    summary["IsActive"] = summary["IsActive"] == "Y"

    # Get home club name
    qry = "%s/club/%s" % (GLOBAL_MPSERVER, summary["HomeClubID"])
    try:
        club = requests.get(qry).json()[0]["ClubName"]
    except IndexError:  # server down or some error
        club = "Unknown"

    # get balance
    last_tran = (
        MemberTransaction.objects.filter(member=user).order_by("created_date").last()
    )
    balance = last_tran.balance if last_tran else "Nil"
    # get auto top up
    auto_button = user.stripe_auto_confirmed == "On"
    events_list = MemberTransaction.objects.filter(member=user).order_by(
        "-created_date"
    )

    return summary, club, balance, auto_button, events_list


#####################
# statement         #
#####################
@login_required()
def statement(request):
    """Member statement view.

    Basic view of statement showing transactions in a web page.

    Args:
        request - standard request object

    Returns:
        HTTPResponse

    """
    (summary, club, balance, auto_button, events_list) = statement_common(request.user)

    things = cobalt_paginator(request, events_list)

    # Check for refund eligible items
    payment_static = PaymentStatic.objects.filter(active=True).last()
    ref_date = timezone.now() - timedelta(weeks=payment_static.stripe_refund_weeks)

    for thing in things:
        if (
            thing.stripe_transaction
            and thing.stripe_transaction.stripe_receipt_url
            and thing.stripe_transaction.status != "Refunded"
            and balance - thing.amount >= 0.0
            and thing.created_date > ref_date
        ):
            thing.show_refund = True

    return render(
        request,
        "payments/statement.html",
        {
            "things": things,
            "user": request.user,
            "summary": summary,
            "club": club,
            "balance": balance,
            "auto_button": auto_button,
            "auto_amount": request.user.auto_amount,
        },
    )


################################
# statement_admin_view         #
################################
@rbac_check_role("payments.global.view")
def statement_admin_view(request, member_id):
    """Member statement view for administrators.

    Basic view of statement showing transactions in a web page. Used by an
    administrator to view a members statement

    Args:
        request - standard request object

    Returns:
        HTTPResponse

    """

    user = get_object_or_404(User, pk=member_id)
    (summary, club, balance, auto_button, events_list) = statement_common(user)

    things = cobalt_paginator(request, events_list)

    # See if this admin can process refunds
    refund_administrator = rbac_user_has_role(request.user, "payments.global.edit")

    return render(
        request,
        "payments/statement.html",
        {
            "things": things,
            "user": user,
            "summary": summary,
            "club": club,
            "balance": balance,
            "auto_button": auto_button,
            "auto_amount": user.auto_amount,
            "refund_administrator": refund_administrator,
            "admin_view": True,
        },
    )


#####################
# statement_org     #
#####################
@login_required()
def statement_org(request, org_id):
    """Organisation statement view.

    Basic view of statement showing transactions in a web page.

    Args:
        request: standard request object
        org_id: organisation to view

    Returns:
        HTTPResponse

    """

    organisation = get_object_or_404(Organisation, pk=org_id)

    admin_view = rbac_user_has_role(request.user, "payments.global.view")

    if (
        not rbac_user_has_role(request.user, "payments.manage.%s.view" % org_id)
        and not admin_view
    ):
        return rbac_forbidden(request, "payments.manage.%s.view" % org_id)

    # get balance
    balance = org_balance(organisation, True)

    # get summary
    today = timezone.now()
    ref_date = today - datetime.timedelta(days=30)
    summary = (
        OrganisationTransaction.objects.filter(
            organisation=organisation, created_date__gte=ref_date
        )
        .values("type")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    total = 0.0
    for item in summary:
        total += float(item["total"])

    # get details
    events_list = OrganisationTransaction.objects.filter(
        organisation=organisation
    ).order_by("-created_date")

    things = cobalt_paginator(request, events_list)

    page_balance = {}

    if things:
        page_balance["closing_balance"] = things[0].balance
        page_balance["closing_date"] = things[0].created_date
        earliest = things[len(things) - 1]
        page_balance["opening_balance"] = earliest.balance - earliest.amount
        page_balance["opening_date"] = earliest.created_date

    return render(
        request,
        "payments/statement_org.html",
        {
            "things": things,
            "balance": balance,
            "org": organisation,
            "summary": summary,
            "total": total,
            "page_balance": page_balance,
            "admin_view": admin_view,
        },
    )


#########################
# statement_csv_org     #
#########################
@login_required()
def statement_csv_org(request, org_id):
    """Organisation statement CSV.

    Args:
        request: standard request object
        org_id: organisation to view

    Returns:
        HTTPResponse: CSV

    """

    organisation = get_object_or_404(Organisation, pk=org_id)

    if not rbac_user_has_role(request.user, "payments.manage.%s.view" % org_id):
        if not rbac_user_has_role(request.user, "payments.global.view"):
            return rbac_forbidden(request, "payments.manage.%s.view" % org_id)

    # get details
    events_list = OrganisationTransaction.objects.filter(
        organisation=organisation
    ).order_by("-created_date")

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="statement.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [organisation.name, "Downloaded by %s" % request.user.full_name, today]
    )
    writer.writerow(
        [
            "Date",
            "Counterparty",
            "Reference",
            "Type",
            "Description",
            "Amount",
            "Balance",
        ]
    )

    for row in events_list:
        counterparty = ""
        if row.member:
            counterparty = row.member
        if row.other_organisation:
            counterparty = row.other_organisation

        local_dt = timezone.localtime(row.created_date, TZ)
        writer.writerow(
            [
                dateformat.format(local_dt, "Y-m-d H:i:s"),
                counterparty,
                row.reference_no,
                row.type,
                row.description,
                row.amount,
                row.balance,
            ]
        )

    return response


def statement_org_summary_ajax(request, org_id, range):
    """Called by the org statement when the summary date range changes

    Args:
        request (HTTPRequest): standard request object
        org_id(int): pk of the org to query
        range(str): range to include in summary

    Returns:
        HTTPResponse: data for table

    """
    if request.method == "GET":

        organisation = get_object_or_404(Organisation, pk=org_id)

        if not rbac_user_has_role(request.user, "payments.manage.%s.view" % org_id):
            if not rbac_user_has_role(request.user, "payments.global.view"):
                return rbac_forbidden(request, "payments.manage.%s.view" % org_id)

        if range == "All":
            summary = (
                OrganisationTransaction.objects.filter(organisation=organisation)
                .values("type")
                .annotate(total=Sum("amount"))
                .order_by("-total")
            )
        else:
            days = int(range)
            today = timezone.now()
            ref_date = today - datetime.timedelta(days=days)
            summary = (
                OrganisationTransaction.objects.filter(
                    organisation=organisation, created_date__gte=ref_date
                )
                .values("type")
                .annotate(total=Sum("amount"))
                .order_by("-total")
            )

    total = 0.0
    for item in summary:
        total = total + float(item["total"])

    return render(
        request,
        "payments/statement_org_summary_ajax.html",
        {"summary": summary, "total": total},
    )


#####################
# statement_csv     #
#####################
@login_required()
def statement_csv(request, member_id=None):
    """Member statement view - csv download

    Generates a CSV of the statement.

    Args:
        request (HTTPRequest): standard request object
        member_id(int): id of member to view, defaults to logged in user

    Returns:
        HTTPResponse: CSV headed response with CSV statement data

    """

    if member_id:
        if not rbac_user_has_role(request.user, "payments.global.view"):
            return rbac_forbidden(request, "payments.global.view")
        member = get_object_or_404(User, pk=member_id)
    else:
        member = request.user

    (summary, club, balance, auto_button, events_list) = statement_common(member)

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="statement.csv"'

    writer = csv.writer(response)
    writer.writerow([member.full_name, member.system_number, today])
    writer.writerow(
        [
            "Date",
            "Counterparty",
            "Reference",
            "Type",
            "Description",
            "Amount",
            "Balance",
        ]
    )

    for row in events_list:
        counterparty = ""
        if row.other_member:
            counterparty = row.other_member
        if row.organisation:
            counterparty = row.organisation
        local_dt = timezone.localtime(row.created_date, TZ)
        writer.writerow(
            [
                dateformat.format(local_dt, "Y-m-d H:i:s"),
                counterparty,
                row.reference_no,
                row.type,
                row.description,
                row.amount,
                row.balance,
            ]
        )

    return response


#####################
# statement_pdf     #
#####################
@login_required()
def statement_pdf(request):
    """Member statement view - csv download

    Generates a PDF of the statement.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse: PDF headed response with PDF statement data


    """
    #    (summary, club, balance, auto_button, events_list) = statement_common(
    #        request
    #    )  # pylint: disable=unused-variable

    #    today = datetime.today().strftime("%-d %B %Y")

    # return render_to_pdf_response(
    #     request,
    #     "payments/statement_pdf.html",
    #     {
    #         "events": events_list,
    #         "user": request.user,
    #         "summary": summary,
    #         "club": club,
    #         "balance": balance,
    #         "today": today,
    #     },
    # )

    return


############################
# Stripe_create_customer   #
############################
@login_required()
def stripe_create_customer(request):
    """calls Stripe to register a customer.

    Creates a new customer entry with Stripe and sets this member's
    stripe_customer_id to match the customer created. Also sets the
    auto_amount for the member to the system default.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        Nothing.
    """

    stripe.api_key = STRIPE_SECRET_KEY
    customer = stripe.Customer.create(
        name=request.user,
        email=request.user.email,
        metadata={"cobalt_tran_type": "Auto"},
    )
    request.user.stripe_customer_id = customer.id
    request.user.auto_amount = AUTO_TOP_UP_DEFAULT_AMT
    request.user.save()


#######################
# setup_autotopup     #
#######################
@login_required()
def setup_autotopup(request):
    """view to sign up to auto top up.

    Creates Stripe customer if not already defined.
    Hands over to Stripe to process card.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse: Our page with Stripe code embedded.

    """
    stripe.api_key = STRIPE_SECRET_KEY
    warn = ""

    # Already set up?
    if request.user.stripe_auto_confirmed == "On":
        try:
            paylist = stripe.PaymentMethod.list(
                customer=request.user.stripe_customer_id,
                type="card",
            )
        except stripe.error.InvalidRequestError as error:
            log_event(
                user=request.user.full_name,
                severity="HIGH",
                source="Payments",
                sub_source="setup_autotopup",
                message="Stripe InvalidRequestError: %s" % error.error.message,
            )
            stripe_create_customer(request)
            paylist = None

        except stripe.error.RateLimitError:
            log_event(
                user=request.user.full_name,
                severity="HIGH",
                source="Payments",
                sub_source="setup_autotopup",
                message="Stripe RateLimitError",
            )

        except stripe.error.AuthenticationError:
            log_event(
                user=request.user.full_name,
                severity="CRITICAL",
                source="Payments",
                sub_source="setup_autotopup",
                message="Stripe AuthenticationError",
            )

        except stripe.error.APIConnectionError:
            log_event(
                user=request.user.full_name,
                severity="HIGH",
                source="Payments",
                sub_source="setup_autotopup",
                message="Stripe APIConnectionError - likely network problems",
            )

        except stripe.error.StripeError:
            log_event(
                user=request.user.full_name,
                severity="CRITICAL",
                source="Payments",
                sub_source="setup_autotopup",
                message="Stripe generic StripeError",
            )

        if paylist:  # if customer has a card associated
            card = paylist.data[0].card
            card_type = card.brand
            card_exp_month = card.exp_month
            card_exp_year = card.exp_year
            card_last4 = card.last4
            warn = f"Changing card details will override your {card_type} card ending in {card_last4} \
                    with expiry {card_exp_month}/{card_exp_year}"

    else:
        stripe_create_customer(request)

    balance = get_balance(request.user)
    topup = request.user.auto_amount

    return render(
        request,
        "payments/autotopup.html",
        {"warn": warn, "topup": topup, "balance": balance},
    )


#######################
# member_transfer     #
#######################
@login_required()
def member_transfer(request):
    """view to transfer $ to another member

    This view allows a member to transfer money to another member.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse

    """

    if request.method == "POST":
        form = MemberTransfer(request.POST, user=request.user)
        if form.is_valid():
            return payment_api(
                request=request,
                description=form.cleaned_data["description"],
                amount=form.cleaned_data["amount"],
                member=request.user,
                other_member=form.cleaned_data["transfer_to"],
                payment_type="Member Transfer",
            )
        else:
            print(form.errors)
    else:
        form = MemberTransfer(user=request.user)

    # get balance
    last_tran = MemberTransaction.objects.filter(member=request.user).last()
    if last_tran:
        balance = last_tran.balance
    else:
        balance = "Nil"

    recents = (
        MemberTransaction.objects.filter(member=request.user)
        .exclude(other_member=None)
        .values("other_member")
        .distinct()
    )
    recent_transfer_to = []
    for r in recents:
        member = User.objects.get(pk=r["other_member"])
        recent_transfer_to.append(member)

    team_mates = TeamMate.objects.filter(user=request.user)
    for team_mate in team_mates:
        recent_transfer_to.append(team_mate.team_mate)

    # make unique - convert to set to be unique, then back to list to sort
    recent_transfer_to = list(set(recent_transfer_to))
    recent_transfer_to.sort(key=lambda x: x.first_name)

    return render(
        request,
        "payments/member_transfer.html",
        {"form": form, "recents": recent_transfer_to, "balance": balance},
    )


########################
# update_auto_amount   #
########################
@login_required()
def update_auto_amount(request):
    """Called by the auto top up page when a user changes the amount of the auto top up.

    The auto top up page has Stripe code on it so a standard form won't work
    for this. Instead we use a little Ajax code on the page to handle this.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse: "Successful"

    """
    if request.method == "GET":
        amount = request.GET["amount"]
        request.user.auto_amount = amount
        request.user.save()

    return HttpResponse("Successful")


###################
# manual_topup    #
###################
@login_required()
def manual_topup(request):
    """Page to allow credit card top up regardless of auto status.

    This page allows a member to add to their account using a credit card,
    they can do this even if they have already set up for auto top up.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse

    """

    balance = get_balance(request.user)

    if request.method == "POST":
        form = ManualTopup(request.POST, balance=balance)
        if form.is_valid():
            if form.cleaned_data["card_choice"] == "Existing":  # Use Auto
                (return_code, msg) = auto_topup_member(
                    request.user,
                    topup_required=form.cleaned_data["amount"],
                    payment_type="Manual Top Up",
                )
                if return_code:  # success
                    messages.success(request, msg, extra_tags="cobalt-message-success")
                    return redirect("payments:payments")
                else:  # error
                    messages.error(request, msg, extra_tags="cobalt-message-error")
            else:  # Use Manual
                trans = StripeTransaction()
                trans.description = "Manual Top Up"
                trans.amount = form.cleaned_data["amount"]
                trans.member = request.user
                trans.save()
                msg = "Manual Top Up - Checkout"
                return render(
                    request, "payments/checkout.html", {"trans": trans, "msg": msg}
                )
        # else:
        #     print(form.errors)

    else:
        form = ManualTopup(balance=balance)

    return render(
        request,
        "payments/manual_topup.html",
        {
            "form": form,
            "balance": balance,
            "remaining_balance": AUTO_TOP_UP_MAX_AMT - balance,
        },
    )


######################
# cancel_auto_top_up #
######################
@login_required()
def cancel_auto_top_up(request):
    """Cancel auto top up.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    if request.method == "POST":
        if request.POST.get("stop_auto"):
            request.user.auto_amount = None
            request.user.stripe_auto_confirmed = "Off"
            request.user.stripe_customer_id = None
            request.user.save()

            messages.info(
                request, "Auto top up disabled", extra_tags="cobalt-message-success"
            )
            return redirect("payments:payments")
        else:
            return redirect("payments:payments")

    balance = get_balance(request.user)
    return render(request, "payments/cancel_autotopup.html", {"balance": balance})


###########################
# statement_admin_summary #
###########################
@rbac_check_role("payments.global.view")
def statement_admin_summary(request):
    """Main statement page for system administrators

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    # Member summary
    total_members = User.objects.count()
    auto_top_up = User.objects.filter(stripe_auto_confirmed="On").count()

    members_list = MemberTransaction.objects.order_by(
        "member", "-created_date"
    ).distinct("member")

    # exclude zeros
    total_balance_members_list = []
    for member in members_list:
        if member.balance != 0:
            total_balance_members_list.append(member)

    total_balance_members = 0
    members_with_balances = 0
    for item in total_balance_members_list:
        total_balance_members += item.balance
        members_with_balances += 1

    # Organisation summary
    total_orgs = Organisation.objects.count()

    orgs_list = OrganisationTransaction.objects.order_by(
        "organisation", "-created_date"
    ).distinct("organisation")

    # exclude zeros
    total_balance_orgs_list = []
    for org in orgs_list:
        if org.balance != 0:
            total_balance_orgs_list.append(org)

    orgs_with_balances = 0
    total_balance_orgs = 0
    for item in total_balance_orgs_list:
        total_balance_orgs += item.balance
        orgs_with_balances += 1

    # Stripe Summary
    today = timezone.now()
    ref_date = today - datetime.timedelta(days=30)
    stripe = (
        StripeTransaction.objects.filter(created_date__gte=ref_date)
        .exclude(stripe_method=None)
        .aggregate(Sum("amount"))
    )

    stripe_balance = stripe_current_balance()

    return render(
        request,
        "payments/statement_admin_summary.html",
        {
            "total_members": total_members,
            "auto_top_up": auto_top_up,
            "total_balance_members": total_balance_members,
            "total_orgs": total_orgs,
            "total_balance_orgs": total_balance_orgs,
            "members_with_balances": members_with_balances,
            "orgs_with_balances": orgs_with_balances,
            "balance": total_balance_orgs + total_balance_members,
            "stripe": stripe,
            "stripe_balance": stripe_balance,
        },
    )


##############
# settlement #
##############
@login_required()
@transaction.atomic
def settlement(request):
    """process payments to organisations. This is expected to be a monthly
        activity.

    At certain points in time an administrator will clear out the balances of
    the organisations accounts and transfer actual money to them through the
    banking system. This is not currently possible to do electronically so this
    is a manual process.

    The administrator should use this list to match with the bank transactions and
    then confirm through this view that the payments have been made.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    if not rbac_user_has_role(request.user, "payments.global.edit"):
        return rbac_forbidden(request, "payments.global.edit")

    payment_static = PaymentStatic.objects.filter(active="True").last()

    if not payment_static:
        return HttpResponse("<h1>Payment Static has not been set up</h1>")

    # orgs with outstanding balances
    # Django is a bit too clever here so we actually have to include balance=0.0 and filter
    # it in the code, otherwise we get the most recent non-zero balance. There may be
    # a way to do this but I couldn't figure it out.
    orgs = OrganisationTransaction.objects.order_by(
        "organisation", "-created_date"
    ).distinct("organisation")
    org_list = []

    non_zero_orgs = []
    for org in orgs:
        if org.balance != 0.0:
            org_list.append((org.id, org.organisation.name))
            non_zero_orgs.append(org)

    if request.method == "POST":

        form = SettlementForm(request.POST, orgs=org_list)
        if form.is_valid():

            # load balances - Important! Do not get the current balance for an
            # org as this may have changed. Use the list confirmed by the user.
            settlement_ids = form.cleaned_data["settle_list"]
            settlements = OrganisationTransaction.objects.filter(pk__in=settlement_ids)

            if "export" in request.POST:  # CSV download

                local_dt = timezone.localtime(timezone.now(), TZ)
                today = dateformat.format(local_dt, "Y-m-d H:i:s")

                response = HttpResponse(content_type="text/csv")
                response[
                    "Content-Disposition"
                ] = 'attachment; filename="settlements.csv"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        "Settlements Export",
                        "Downloaded by %s" % request.user.full_name,
                        today,
                    ]
                )
                writer.writerow(
                    [
                        "CLub Number",
                        "CLub Name",
                        "BSB",
                        "Account Number",
                        "Gross Amount",
                        f"{GLOBAL_ORG} fees %",
                        "Settlement Amount",
                    ]
                )

                for org in settlements:
                    writer.writerow(
                        [
                            org.organisation.org_id,
                            org.organisation.name,
                            org.organisation.bank_bsb,
                            org.organisation.bank_account,
                            org.balance,
                            org.organisation.settlement_fee_percent,
                            org.settlement_amount,
                        ]
                    )

                return response

            else:  # confirm payments

                trans_list = []
                total = 0.0

                system_org = get_object_or_404(Organisation, pk=GLOBAL_ORG_ID)

                # Remove money from org accounts
                for item in settlements:
                    total += float(item.balance)
                    trans = update_organisation(
                        organisation=item.organisation,
                        other_organisation=system_org,
                        amount=-item.balance,
                        description=f"Settlement from {GLOBAL_ORG}. Fees {item.organisation.settlement_fee_percent}%. Net Bank Transfer: {GLOBAL_CURRENCY_SYMBOL}{item.settlement_amount}.",
                        log_msg=f"Settlement from {GLOBAL_ORG} to {item.organisation}",
                        source="payments",
                        sub_source="settlements",
                        payment_type="Settlement",
                    )
                    trans_list.append(trans)

                messages.success(
                    request,
                    "Settlement processed successfully.",
                    extra_tags="cobalt-message-success",
                )
                return render(
                    request,
                    "payments/settlement-complete.html",
                    {"trans": trans_list, "total": total},
                )

    else:
        form = SettlementForm(orgs=org_list)

    return render(
        request, "payments/settlement.html", {"orgs": non_zero_orgs, "form": form}
    )


########################
# manual_adjust_member #
########################
@login_required()
def manual_adjust_member(request):
    """make a manual adjustment on a member account

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    if not rbac_user_has_role(request.user, "payments.global.edit"):
        return rbac_forbidden(request, "payments.global.edit")

    if request.method == "POST":
        form = AdjustMemberForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data["member"]
            amount = form.cleaned_data["amount"]
            description = form.cleaned_data["description"]
            update_account(
                member=member,
                amount=amount,
                description=description,
                log_msg="Manual adjustment by %s %s %s"
                % (request.user, member, amount),
                source="payments",
                sub_source="manual_adjust_member",
                payment_type="Manual Adjustment",
                other_member=request.user,
            )
            msg = "Manual adjustment successful. %s adjusted by %s%s" % (
                member,
                GLOBAL_CURRENCY_SYMBOL,
                amount,
            )
            messages.success(request, msg, extra_tags="cobalt-message-success")
            return redirect("payments:statement_admin_summary")

    else:
        form = AdjustMemberForm()

        return render(request, "payments/manual_adjust_member.html", {"form": form})


########################
# manual_adjust_org    #
########################
@login_required()
def manual_adjust_org(request):
    """make a manual adjustment on an organisation account

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    if not rbac_user_has_role(request.user, "payments.global.edit"):
        return rbac_forbidden(request, "payments.global.edit")

    if request.method == "POST":
        form = AdjustOrgForm(request.POST)
        if form.is_valid():
            org = form.cleaned_data["organisation"]
            amount = form.cleaned_data["amount"]
            description = form.cleaned_data["description"]
            update_organisation(
                organisation=org,
                amount=amount,
                description=description,
                log_msg=description,
                source="payments",
                sub_source="manual_adjustment_org",
                payment_type="Manual Adjustment",
                member=request.user,
            )
            msg = "Manual adjustment successful. %s adjusted by %s%s" % (
                org,
                GLOBAL_CURRENCY_SYMBOL,
                amount,
            )
            messages.success(request, msg, extra_tags="cobalt-message-success")
            return redirect("payments:statement_admin_summary")

    else:
        form = AdjustOrgForm()

        return render(request, "payments/manual_adjust_org.html", {"form": form})


##########################
# stripe_webpage_confirm #
##########################
@login_required()
def stripe_webpage_confirm(request, stripe_id):
    """User has been told by Stripe that transaction went through.

    This is called by the web page after Stripe confirms the transaction is approved.
    Because this originates from the client we do not trust it, but we do move
    the status to Pending unless it is already Confirmed (timing issues).

    Args:
        request(HTTPRequest): stasndard request object
        stripe_id(int):  pk of stripe transaction

    Returns:
        Nothing.
    """

    stripe = get_object_or_404(StripeTransaction, pk=stripe_id)
    if stripe.status == "Intent":
        print("Stripe status is intend - updating")
        stripe.status = "Pending"
        stripe.save()

    return HttpResponse("ok")


############################
# stripe_autotopup_confirm #
############################
@login_required()
def stripe_autotopup_confirm(request):
    """User has been told by Stripe that auto top up went through.

    This is called by the web page after Stripe confirms that auto top up is approved.
    Because this originates from the client we do not trust it, but we do move
    the status to Pending unless it is already Confirmed (timing issues).

    For manual payments we update the transaction, but for auto top up there is
    no transaction so we record this on the User object.

    Args:
        request(HTTPRequest): standard request object

    Returns:
        Nothing.
    """

    if request.user.stripe_auto_confirmed == "Off":
        request.user.stripe_auto_confirmed = "Pending"
        request.user.save()

    return HttpResponse("ok")


############################
# stripe_autotopup_confirm #
############################
@login_required()
def stripe_autotopup_off(request):
    """Switch off auto top up

    This is called by the web page when a user submits new card details to
    Stripe. This is the latest point that we can turn it off in case the
    user aborts the change.

    Args:
        request(HTTPRequest): stasndard request object

    Returns:
        Nothing.
    """

    request.user.stripe_auto_confirmed = "Off"
    request.user.save()

    return HttpResponse("ok")


######################
# stripe_pending     #
######################
@login_required()
def stripe_pending(request):
    """Shows any pending stripe transactions.

    Stripe transactions should never really be in a pending state unless
    there is a problem. They go from intent to success usually. The only time
    they will sit in pending is if Stripe is slow to talk to us or there is an
    error.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    if not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.global.view")

    try:
        stripe_latest = StripeTransaction.objects.filter(status="Success").latest(
            "created_date"
        )
        stripe_manual_pending = StripeTransaction.objects.filter(status="Pending")
        stripe_manual_intent = StripeTransaction.objects.filter(
            status="Intent"
        ).order_by("-created_date")[:20]
        stripe_auto_pending = User.objects.filter(stripe_auto_confirmed="Pending")
    except StripeTransaction.DoesNotExist:
        return HttpResponse("No Stripe data found")

    return render(
        request,
        "payments/stripe_pending.html",
        {
            "stripe_manual_pending": stripe_manual_pending,
            "stripe_manual_intent": stripe_manual_intent,
            "stripe_latest": stripe_latest,
            "stripe_auto_pending": stripe_auto_pending,
        },
    )


#################################
#  admin_members_with_balance   #
#################################
@login_required()
def admin_members_with_balance(request):
    """Shows any open balances held by members

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    if not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.global.view")

    members_list = MemberTransaction.objects.order_by(
        "member", "-created_date"
    ).distinct("member")

    # exclude zeros
    members = []
    for member in members_list:
        if member.balance != 0:
            members.append(member)

    things = cobalt_paginator(request, members)

    return render(
        request, "payments/admin_members_with_balance.html", {"things": things}
    )


#################################
#  admin_orgs_with_balance      #
#################################
@login_required()
def admin_orgs_with_balance(request):
    """Shows any open balances held by orgs

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    if not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.global.view")

    orgs_list = OrganisationTransaction.objects.order_by(
        "organisation", "-created_date"
    ).distinct("organisation")

    # exclude zeros
    orgs = []
    for org in orgs_list:
        if org.balance != 0:
            orgs.append(org)

    things = cobalt_paginator(request, orgs)

    return render(request, "payments/admin_orgs_with_balance.html", {"things": things})


#####################################
#  admin_members_with_balance_csv   #
#####################################
@login_required()
def admin_members_with_balance_csv(request):
    """Shows any open balances held by members - as CSV

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse - CSV
    """
    if not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.global.view")

    members_list = MemberTransaction.objects.order_by(
        "member", "-created_date"
    ).distinct("member")

    # exclude zeros
    members = []
    for member in members_list:
        if member.balance != 0:
            members.append(member)

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="member-balances.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["Member Balances", "Downloaded by %s" % request.user.full_name, today]
    )
    writer.writerow(
        ["Member Number", "Member First Name", "Member Last Name", "Balance"]
    )

    for member in members:
        writer.writerow(
            [
                member.member.system_number,
                member.member.first_name,
                member.member.last_name,
                member.balance,
            ]
        )

    return response


#####################################
#  admin_orgs_with_balance_csv      #
#####################################
@login_required()
def admin_orgs_with_balance_csv(request):
    """Shows any open balances held by orgs - as CSV

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse - CSV
    """
    if not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.global.view")

    orgs_list = OrganisationTransaction.objects.order_by(
        "organisation", "-created_date"
    ).distinct("organisation")

    # exclude zeros
    orgs = []
    for org in orgs_list:
        if org.balance != 0:
            orgs.append(org)

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="organisation-balances.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["Organisation Balances", "Downloaded by %s" % request.user.full_name, today]
    )
    writer.writerow(["Club Number", "Club Name", "Balance"])

    for org in orgs:
        writer.writerow([org.organisation.org_id, org.organisation.name, org.balance])

    return response


###################################
# admin_view_manual_adjustments   #
###################################
@login_required()
def admin_view_manual_adjustments(request):
    """Shows any open balances held by orgs - as CSV

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse (Can be CSV)
    """

    if not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.global.view")

    if request.method == "POST":
        form = DateForm(request.POST)
        if form.is_valid():

            # Need to make the dates TZ aware
            to_date_form = form.cleaned_data["to_date"]
            from_date_form = form.cleaned_data["from_date"]
            # date -> datetime
            to_date = datetime.datetime.combine(to_date_form, datetime.time(23, 59))
            from_date = datetime.datetime.combine(from_date_form, datetime.time(0, 0))
            # make aware
            to_date = make_aware(to_date, TZ)
            from_date = make_aware(from_date, TZ)

            manual_member = MemberTransaction.objects.filter(
                type="Manual Adjustment"
            ).filter(created_date__range=(from_date, to_date))
            manual_org = OrganisationTransaction.objects.filter(
                type="Manual Adjustment"
            ).filter(created_date__range=(from_date, to_date))

            if "export" in request.POST:

                local_dt = timezone.localtime(timezone.now(), TZ)
                today = dateformat.format(local_dt, "Y-m-d H:i:s")

                response = HttpResponse(content_type="text/csv")
                response[
                    "Content-Disposition"
                ] = 'attachment; filename="manual-adjustments.csv"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        "Manual Adjustments",
                        "Downloaded by %s" % request.user.full_name,
                        today,
                    ]
                )

                # Members

                writer.writerow(
                    [
                        "Date",
                        "Administrator",
                        "Transaction Type",
                        "User",
                        "Description",
                        "Amount",
                    ]
                )

                for member in manual_member:
                    local_dt = timezone.localtime(member.created_date, TZ)

                    writer.writerow(
                        [
                            dateformat.format(local_dt, "Y-m-d H:i:s"),
                            member.other_member,
                            member.type,
                            member.member,
                            member.description,
                            member.amount,
                        ]
                    )

                # Organisations
                writer.writerow("")
                writer.writerow("")

                writer.writerow(
                    [
                        "Date",
                        "Administrator",
                        "Transaction Type",
                        "Club ID",
                        "Organisation",
                        "Description",
                        "Amount",
                    ]
                )

                for org in manual_org:
                    local_dt = timezone.localtime(member.created_date, TZ)

                    writer.writerow(
                        [
                            dateformat.format(local_dt, "Y-m-d H:i:s"),
                            org.member,
                            org.type,
                            org.organisation.org_id,
                            org.organisation,
                            org.description,
                            org.amount,
                        ]
                    )

                return response

            else:
                return render(
                    request,
                    "payments/admin_view_manual_adjustments.html",
                    {
                        "form": form,
                        "manual_member": manual_member,
                        "manual_org": manual_org,
                    },
                )

        else:
            print(form.errors)

    else:
        form = DateForm()

    return render(
        request, "payments/admin_view_manual_adjustments.html", {"form": form}
    )


###################################
# admin_view_stripe_transactions  #
###################################
@rbac_check_role("payments.global.view")
def admin_view_stripe_transactions(request):
    """Shows stripe transactions for an admin

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse (can be CSV)
    """

    page_no = None

    form = DateForm(request.POST) if request.method == "POST" else DateForm()
    if form.is_valid():

        # Need to make the dates TZ aware
        to_date_form = form.cleaned_data["to_date"]
        from_date_form = form.cleaned_data["from_date"]
        # date -> datetime
        to_date = datetime.datetime.combine(to_date_form, datetime.time(23, 59))
        from_date = datetime.datetime.combine(from_date_form, datetime.time(0, 0))
        # make aware
        to_date = make_aware(to_date, TZ)
        from_date = make_aware(from_date, TZ)

        stripes = (
            StripeTransaction.objects.filter(created_date__range=(from_date, to_date))
            .exclude(stripe_method=None)
            .order_by("-created_date")
        )

        # Go to the first page if this is a new search
        page_no = 1

    else:

        stripes = StripeTransaction.objects.exclude(stripe_method=None).order_by(
            "-created_date"
        )

    # Get payment static
    pay_static = PaymentStatic.objects.filter(active=True).last()
    stripe.api_key = STRIPE_SECRET_KEY

    for stripe_item in stripes:
        stripe_item.amount_settle = (
            float(stripe_item.amount) - float(pay_static.stripe_cost_per_transaction)
        ) * (1.0 - float(pay_static.stripe_percentage_charge) / 100.0)

        # We used to go to Stripe to get the details but it times out even if the list is quite small.

    if "export" in request.POST:

        local_dt = timezone.localtime(timezone.now(), TZ)
        today = dateformat.format(local_dt, "Y-m-d H:i:s")

        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = 'attachment; filename="stripe-transactions.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Stripe Transactions",
                "Downloaded by %s" % request.user.full_name,
                today,
            ]
        )

        writer.writerow(
            [
                "Date",
                "Status",
                "member",
                "Amount",
                "Refund Amount",
                "Expected Settlement Amount",
                "Description",
                "stripe_reference",
                "stripe_exp_month",
                "stripe_exp_year",
                "stripe_last4",
                "linked_organisation",
                "linked_member",
                "linked_transaction_type",
                "linked_amount",
                "stripe_receipt_url",
            ]
        )

        for stripe_item in stripes:
            local_dt = timezone.localtime(stripe_item.created_date, TZ)

            writer.writerow(
                [
                    dateformat.format(local_dt, "Y-m-d H:i:s"),
                    stripe_item.status,
                    stripe_item.member,
                    stripe_item.amount,
                    stripe_item.refund_amount,
                    stripe_item.amount_settle,
                    stripe_item.description,
                    stripe_item.stripe_reference,
                    stripe_item.stripe_exp_month,
                    stripe_item.stripe_exp_year,
                    stripe_item.stripe_last4,
                    stripe_item.linked_organisation,
                    stripe_item.linked_member,
                    stripe_item.linked_transaction_type,
                    stripe_item.linked_amount,
                    stripe_item.stripe_receipt_url,
                ]
            )
        return response

    else:
        things = cobalt_paginator(request, stripes, page_no=page_no)
        return render(
            request,
            "payments/admin_view_stripe_transactions.html",
            {"form": form, "things": things},
        )


##########################################
# admin_view_stripe_transaction_details  #
##########################################


@rbac_check_role("payments.global.view")
def admin_view_stripe_transaction_detail(request, stripe_transaction_id):
    """Shows stripe transaction details for an admin

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    stripe_item = get_object_or_404(StripeTransaction, pk=stripe_transaction_id)

    payment_static = PaymentStatic.objects.filter(active="True").last()

    if not payment_static:
        return HttpResponse("<h1>Payment Static has not been set up</h1>")

    stripe.api_key = STRIPE_SECRET_KEY
    if stripe_item.stripe_balance_transaction:

        balance_tran = stripe.BalanceTransaction.retrieve(
            stripe_item.stripe_balance_transaction
        )
        stripe_item.stripe_fees = balance_tran.fee / 100.0
        stripe_item.stripe_fee_details = balance_tran.fee_details
        for row in stripe_item.stripe_fee_details:
            row.amount = row.amount / 100.0
        stripe_item.stripe_settlement = balance_tran.net / 100.0
        stripe_item.stripe_created_date = datetime.datetime.fromtimestamp(
            balance_tran.created
        )
        stripe_item.stripe_available_on = datetime.datetime.fromtimestamp(
            balance_tran.available_on
        )
        stripe_item.stripe_percentage_charge = (
            100.0
            * (float(stripe_item.amount) - float(stripe_item.stripe_settlement))
            / float(stripe_item.amount)
        )
        our_estimate_fee = float(stripe_item.amount) * float(
            payment_static.stripe_percentage_charge
        ) / 100.0 + float(payment_static.stripe_cost_per_transaction)
        our_estimate_fee_percent = our_estimate_fee * 100.0 / float(stripe_item.amount)
        stripe_item.our_estimate_fee = "%.2f" % our_estimate_fee
        stripe_item.our_estimate_fee_percent = "%.2f" % our_estimate_fee_percent
    return render(
        request,
        "payments/admin_view_stripe_transaction_detail.html",
        {"stripe_item": stripe_item},
    )


####################################
# refund_stripe_transaction        #
####################################
@login_required()
def refund_stripe_transaction(request, stripe_transaction_id):
    """Allows a user to refund a Stripe transaction

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    stripe_item = get_object_or_404(StripeTransaction, pk=stripe_transaction_id)

    # Calculate how much refund is left in case already partly refunded
    stripe_item.refund_left = stripe_item.amount - stripe_item.refund_amount

    member_balance = get_balance(stripe_item.member)
    payment_static = PaymentStatic.objects.filter(active=True).last()
    balance_after = float(member_balance) - float(stripe_item.refund_left)
    bridge_credit_charge = float(stripe_item.refund_left)
    member_card_refund = (
        bridge_credit_charge
        * (100.0 - float(payment_static.stripe_refund_percentage_charge))
        / 100.0
    )

    # Is this allowed?

    if stripe_item.member != request.user:
        messages.error(
            request,
            "Action Prohibited - transaction is not yours",
            extra_tags="cobalt-message-error",
        )
        return redirect("payments:statement")

    if not stripe_item.stripe_receipt_url:
        messages.error(
            request,
            "Invalid transaction for a refund",
            extra_tags="cobalt-message-error",
        )
        return redirect("payments:statement")

    if stripe_item.status == "Refunded":
        messages.error(
            request, "Transaction already refunded", extra_tags="cobalt-message-error"
        )
        return redirect("payments:statement")

    if not balance_after >= 0.0:
        messages.error(
            request,
            "Cannot refund. Balance will be negative",
            extra_tags="cobalt-message-error",
        )
        return redirect("payments:statement")

    if not stripe_current_balance() - bridge_credit_charge >= 0.0:
        messages.error(
            request,
            "Cannot refund. We have insufficient funds available with Stripe. Please try again later.",
            extra_tags="cobalt-message-error",
        )
        return redirect("payments:statement")

    ref_date = timezone.now() - timedelta(weeks=payment_static.stripe_refund_weeks)
    if stripe_item.created_date <= ref_date:
        messages.error(
            request,
            "Cannot refund. Transaction is too old.",
            extra_tags="cobalt-message-error",
        )
        return redirect("payments:statement")

    if request.method == "POST":

        stripe_amount = int(member_card_refund * 100)

        stripe.api_key = STRIPE_SECRET_KEY

        try:
            rc = stripe.Refund.create(
                charge=stripe_item.stripe_reference,
                amount=stripe_amount,
            )

        except stripe.error.InvalidRequestError as e:
            log_event(
                user=request.user.full_name,
                severity="HIGH",
                source="Payments",
                sub_source="User initiated refund",
                message=str(e),
            )

            return render(
                request,
                "payments/payments_refund_error.html",
                {"rc": e, "stripe_item": stripe_item},
            )

        if rc["status"] != "succeeded":
            return render(
                request,
                "payments/payments_refund_error.html",
                {"rc": rc, "stripe_item": stripe_item},
            )

        # Call atomic database update
        _refund_stripe_transaction_sub(
            stripe_item, stripe_item.refund_left, "Card refund"
        )

        # Notify member
        email_body = f"""You have requested to refund a card transaction. You will receive a refund of
        {GLOBAL_CURRENCY_SYMBOL}{member_card_refund:.2f} to your card.<br><br>
         Please note that It can take up to two weeks for the money to appear in your card statement.<br><br>
         Your {BRIDGE_CREDITS} account balance has been reduced to reflect this refund. You can check your new balance
         using the link below.<br><br>
         """
        context = {
            "name": stripe_item.member.first_name,
            "title": "Card Refund",
            "email_body": email_body,
            "host": COBALT_HOSTNAME,
            "link": "/payments",
            "link_text": "View Statement",
        }

        html_msg = render_to_string("notifications/email_with_button.html", context)

        # send
        contact_member(
            member=stripe_item.member,
            msg="Card Refund - %s%s" % (GLOBAL_CURRENCY_SYMBOL, member_card_refund),
            contact_type="Email",
            html_msg=html_msg,
            link="/payments",
            subject="Card Refund",
        )

        messages.success(
            request, "Refund Request Submitted", extra_tags="cobalt-message-success"
        )
        return redirect("payments:statement")

    return render(
        request,
        "payments/refund_stripe_transaction.html",
        {
            "stripe_item": stripe_item,
            "payment_static": payment_static,
            "member_balance": member_balance,
            "balance_after": balance_after,
            "bridge_credit_charge": bridge_credit_charge,
            "member_card_refund": member_card_refund,
        },
    )


##########################################
# admin_refund_stripe_transaction        #
##########################################
@rbac_check_role("payments.global.edit")
def admin_refund_stripe_transaction(request, stripe_transaction_id):
    """Allows an Admin to refund a Stripe transaction

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    stripe_item = get_object_or_404(StripeTransaction, pk=stripe_transaction_id)

    if stripe_item.member == request.user:
        messages.error(
            request,
            "You cannot refund your own transactions. Do it through Stripe, their security isn't as good as ours.",
            extra_tags="cobalt-message-error",
        )
        return redirect("payments:admin_view_stripe_transactions")

    # Calculate how much refund is left
    stripe_item.refund_left = stripe_item.amount - stripe_item.refund_amount

    member_balance = get_balance(stripe_item.member)

    if request.method == "POST":
        print(stripe_item.refund_left)
        form = StripeRefund(request.POST, payment_amount=stripe_item.refund_left)
        if form.is_valid():

            # Check if this the first entry screen or the confirmation screen
            if "first-submit" in request.POST:
                # First screen so show user the confirm
                after_balance = float(member_balance) - float(
                    form.cleaned_data["amount"]
                )
                return render(
                    request,
                    "payments/admin_refund_stripe_transaction_confirm.html",
                    {
                        "stripe_item": stripe_item,
                        "form": form,
                        "after_balance": after_balance,
                    },
                )

            elif "confirm-submit" in request.POST:
                # Confirm screen so make refund

                amount = form.cleaned_data["amount"]
                description = form.cleaned_data["description"]

                # Stripe uses cents not dollars
                stripe_amount = int(amount * 100)

                try:
                    rc = stripe.Refund.create(
                        charge=stripe_item.stripe_reference,
                        amount=stripe_amount,
                    )

                except stripe.error.InvalidRequestError as e:
                    log_event(
                        user=request.user.full_name,
                        severity="HIGH",
                        source="Payments",
                        sub_source="Admin refund",
                        message=str(e),
                    )

                    return render(
                        request,
                        "payments/payments_refund_error.html",
                        {"rc": e, "stripe_item": stripe_item},
                    )

                if rc["status"] != "succeeded":
                    return render(
                        request,
                        "payments/payments_refund_error.html",
                        {"rc": rc, "stripe_item": stripe_item},
                    )

                # Call atomic database update
                _refund_stripe_transaction_sub(
                    stripe_item, amount, description, counterparty=request.user
                )

                # Notify member
                email_body = f"""<b>{request.user.full_name}</b> has refunded {GLOBAL_CURRENCY_SYMBOL}{amount:.2f}
                 to your card.<br><br>
                 The description was: {description}<br><br>
                 Please note that It can take up to two weeks for the money to appear in your card statement.<br><br>
                 Your {BRIDGE_CREDITS} account balance has been reduced to reflect this refund.<br><br>
                 You can view your statement by clicking on the link below<br><br>
                 """
                context = {
                    "name": stripe_item.member.first_name,
                    "title": "Card Refund",
                    "email_body": email_body,
                    "host": COBALT_HOSTNAME,
                    "link": "/payments",
                    "link_text": "View Statement",
                }

                html_msg = render_to_string(
                    "notifications/email_with_button.html", context
                )

                # send
                contact_member(
                    member=stripe_item.member,
                    msg="Card Refund - %s%s" % (GLOBAL_CURRENCY_SYMBOL, amount),
                    contact_type="Email",
                    html_msg=html_msg,
                    link="/payments",
                    subject="Card Refund",
                )

                log_event(
                    user=stripe_item.member,
                    severity="INFO",
                    source="Payments",
                    sub_source="Admin refund",
                    message=f"{request.user} refunded {GLOBAL_CURRENCY_SYMBOL}{amount} to {stripe_item.member.full_name}",
                )

                msg = f"Refund Successful. Paid {GLOBAL_CURRENCY_SYMBOL}{amount} to {stripe_item.member}"
                messages.success(request, msg, extra_tags="cobalt-message-success")
                return redirect("payments:admin_view_stripe_transactions")

    else:
        form = StripeRefund(payment_amount=stripe_item.refund_left)
        form.fields["amount"].initial = stripe_item.refund_left
        form.fields["description"].initial = "Card Refund"

    return render(
        request,
        "payments/admin_refund_stripe_transaction.html",
        {"stripe_item": stripe_item, "form": form, "member_balance": member_balance},
    )


@atomic
def _refund_stripe_transaction_sub(stripe_item, amount, description, counterparty=None):
    """Atomic transaction update for refunds"""

    # Update the Stripe transaction
    if amount + stripe_item.refund_amount >= stripe_item.amount:
        stripe_item.status = "Refunded"
    else:
        stripe_item.status = "Partial refund"

    stripe_item.refund_amount += amount

    stripe_item.save()

    # Create a new transaction for the user
    balance = get_balance(stripe_item.member) - float(amount)

    abf = get_object_or_404(Organisation, pk=GLOBAL_ORG_ID)

    act = MemberTransaction()
    act.member = stripe_item.member
    act.amount = -amount
    # Linking to the stripe transaction messes up the statements
    # act.stripe_transaction = stripe_item
    act.balance = balance
    act.description = description
    act.organisation = abf
    act.type = "Card Refund"

    act.save()

    log_event(
        user=stripe_item.member.full_name,
        severity="INFO",
        source="Payments",
        sub_source="Card Refund",
        message=description,
    )


@login_required()
def member_transfer_org(request, org_id):
    """Allows an organisation to transfer money to a member

    Args:
        request (HTTPRequest): standard request object
        org_id (int): organisation doing the transfer

    Returns:
        HTTPResponse
    """

    organisation = get_object_or_404(Organisation, pk=org_id)

    if not rbac_user_has_role(
        request.user, "payments.manage.%s.view" % org_id
    ) and not rbac_user_has_role(request.user, "payments.global.view"):
        return rbac_forbidden(request, "payments.manage.%s.view" % org_id)

    balance = org_balance(organisation)

    if request.method == "POST":
        form = MemberTransferOrg(request.POST, balance=balance)
        if form.is_valid():
            member = form.cleaned_data["transfer_to"]
            amount = form.cleaned_data["amount"]
            description = form.cleaned_data["description"]

            # Org transaction
            update_organisation(
                organisation=organisation,
                description=description,
                amount=-amount,
                log_msg=f"Transfer from {organisation} to {member}",
                source="payments",
                sub_source="member_transfer_org",
                payment_type="Member Transfer",
                member=member,
            )

            update_account(
                member=member,
                amount=amount,
                description=description,
                log_msg=f"Transfer to {member} from {organisation}",
                source="payments",
                sub_source="member_transfer_org",
                payment_type="Org Transfer",
                organisation=organisation,
            )

            # Notify member
            email_body = f"<b>{organisation}</b> has transferred {GLOBAL_CURRENCY_SYMBOL}{amount:.2f} into your {BRIDGE_CREDITS} account.<br><br>The description was: {description}.<br><br>Please contact {organisation} directly if you have any queries. This transfer was made by {request.user}.<br><br>"
            context = {
                "name": member.first_name,
                "title": "Transfer from %s" % organisation,
                "email_body": email_body,
                "host": COBALT_HOSTNAME,
                "link": "/payments",
                "link_text": "View Statement",
            }

            html_msg = render_to_string("notifications/email_with_button.html", context)

            # send
            contact_member(
                member=member,
                msg="Transfer from %s - %s%s"
                % (organisation, GLOBAL_CURRENCY_SYMBOL, amount),
                contact_type="Email",
                html_msg=html_msg,
                link="/payments",
                subject="Transfer from %s" % organisation,
            )

            msg = "Transferred %s%s to %s" % (
                GLOBAL_CURRENCY_SYMBOL,
                amount,
                member,
            )
            messages.success(request, msg, extra_tags="cobalt-message-success")
            return redirect("payments:statement_org", org_id=organisation.id)
        else:
            print(form.errors)
    else:
        form = MemberTransferOrg(balance=balance)

    return render(
        request,
        "payments/member_transfer_org.html",
        {"form": form, "balance": balance, "org": organisation},
    )


@rbac_check_role("payments.global.edit")
def admin_payments_static(request):
    """Manage static data for payments

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    payment_static = PaymentStatic.objects.filter(active=True).last()

    if payment_static:
        form = PaymentStaticForm(instance=payment_static)
    else:
        form = PaymentStaticForm()

    if request.method == "POST":
        form = PaymentStaticForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.modified_by = request.user
            obj.save()

            # set all others to be inactive
            PaymentStatic.objects.all().update(active=False)

            # set this one active
            payment_static = PaymentStatic.objects.order_by("id").last()
            payment_static.active = True
            payment_static.save()

            messages.success(
                request, "Settings updated", extra_tags="cobalt-message-success"
            )
            return redirect("payments:statement_admin_summary")

    return render(
        request,
        "payments/admin_payments_static.html",
        {"form": form, "payment_static_old": payment_static},
    )


@login_required()
def admin_payments_static_history(request):
    """history for static data for payments

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    if not rbac_user_has_role(request.user, "payments.global.edit"):
        return rbac_forbidden(request, "payments.global.edit")

    payment_statics = PaymentStatic.objects.order_by("-created_date")

    return render(
        request,
        "payments/admin_payments_static_history.html",
        {"payment_statics": payment_statics},
    )


@login_required()
def admin_payments_static_org_override(request):
    """Manage static data for individual orgs (override default values)

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    if not rbac_user_has_role(request.user, "payments.global.edit"):
        return rbac_forbidden(request, "payments.global.edit")

    org_statics = OrganisationSettlementFees.objects.all()

    return render(
        request,
        "payments/admin_payments_static_org_override.html",
        {"org_statics": org_statics},
    )


@login_required()
def admin_payments_static_org_override_add(request):
    """Manage static data for individual orgs (override default values)
    This screen adds an override

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    if not rbac_user_has_role(request.user, "payments.global.edit"):
        return rbac_forbidden(request, "payments.global.edit")

    form = OrgStaticOverrideForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(
                request, "Entry added", extra_tags="cobalt-message-success"
            )
            return redirect("payments:admin_payments_static_org_override")
        else:
            messages.error(request, form.errors, extra_tags="cobalt-message-error")

    return render(
        request,
        "payments/admin_payments_static_org_override_add.html",
        {"form": form},
    )


@rbac_check_role("payments.global.edit")
def admin_payments_static_org_override_delete(request, item_id):
    """Manage static data for individual orgs (override default values)
    This screen deletes an override

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    item = get_object_or_404(OrganisationSettlementFees, pk=item_id)

    item.delete()

    messages.success(request, "Entry deleted", extra_tags="cobalt-message-success")
    return redirect("payments:admin_payments_static_org_override")


@rbac_check_role("payments.global.edit")
def admin_player_payments(request, member_id):
    """Manage a players payments as an admin. E.g. make a refund to a credit card.

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    member = get_object_or_404(User, pk=member_id)
    summary = user_summary(member.system_number)
    balance = get_balance(member)

    stripes = StripeTransaction.objects.filter(member=member).order_by("-created_date")[
        :10
    ]

    return render(
        request,
        "payments/admin_player_payments.html",
        {"profile": member, "summary": summary, "balance": balance, "stripes": stripes},
    )


def _get_member_balance_at_date(ref_date):
    """Internal function to get list of members with balances at specific date"""

    # get latest transaction per member - can't do a Sum after a distinct - not yet supported
    members = (
        MemberTransaction.objects.filter(created_date__lt=ref_date)
        .order_by("member", "-created_date")
        .distinct("member")
        .exclude(balance=0.0)
    )

    members_balance = 0.0

    for member in members:
        members_balance += float(member.balance)

    return members_balance, members


def _get_org_balance_at_date(ref_date):
    """Internal function to get list of organisations with balances at specific date"""

    # get latest transaction per org - can't do a Sum after a distinct - not yet supported
    orgs = (
        OrganisationTransaction.objects.filter(created_date__lt=ref_date)
        .order_by("organisation", "-created_date")
        .distinct("organisation")
        .exclude(balance=0.0)
    )

    orgs_balance = 0.0

    for org in orgs:
        orgs_balance += float(org.balance)

    return orgs_balance, orgs


@rbac_check_role("payments.global.view")
def admin_stripe_rec(request):
    """This will become the Stripe reconciliation. For now it just shows the balances to allow a manual reconciliation

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    ref_date, _ = _admin_stripe_rec_ref_date(request)

    members_balance, members = _get_member_balance_at_date(ref_date)
    orgs_balance, orgs = _get_org_balance_at_date(ref_date)

    return render(
        request,
        "payments/admin_stripe_rec.html",
        {
            "members_balance": members_balance,
            "orgs_balance": orgs_balance,
            "ref_date": ref_date,
            "members_count": members.count(),
            "orgs_count": orgs.count(),
        },
    )


def _admin_stripe_rec_ref_date(request):
    """common function to handle reference date"""

    # Default date is last day of the previous month. Get first of this month and step back 1 day
    ref_date = datetime.datetime.now(tz=TZ).replace(
        day=1, hour=23, minute=59, second=59, microsecond=999_999
    ) - datetime.timedelta(days=1)

    form_date = request.POST.get("ref_date")

    if form_date:
        ref_date = (
            datetime.datetime.strptime(form_date, "%d/%m/%Y")
            .replace(tzinfo=TZ)
            .replace(hour=23, minute=59, second=59, microsecond=999_999)
        )

    # also calculate date a month earlier
    ref_date_month_earlier = ref_date.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ) - datetime.timedelta(days=1)

    return ref_date, ref_date_month_earlier


@rbac_check_role("payments.global.view")
def admin_stripe_rec_download(request):
    """CSV download of all movements for the month prior to the reference date
    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    # Get the ref date
    ref_date, ref_date_month_earlier = _admin_stripe_rec_ref_date(request)

    # Get the 3 different kinds of financial transaction
    members = MemberTransaction.objects.filter(created_date__lte=ref_date).filter(
        created_date__gte=ref_date_month_earlier
    )
    stripes = (
        StripeTransaction.objects.filter(created_date__lte=ref_date)
        .filter(created_date__gte=ref_date_month_earlier)
        .filter(status__in=["Succeeded", "Partial refund", "Refunded"])
    )
    orgs = OrganisationTransaction.objects.filter(created_date__lte=ref_date).filter(
        created_date__gte=ref_date_month_earlier
    )

    # Merge them together
    results = []

    # MemberTransactions
    for member in members:
        counterparty = ""
        if member.other_member:
            counterparty = member.other_member
        if member.organisation:
            counterparty = member.organisation
        item = {
            "table": "Member Transaction",
            "created_date": member.created_date,
            "counterparty": counterparty,
            "reference_no": member.reference_no,
            "type": member.type,
            "description": member.description,
            "amount": member.amount,
            "balance": member.balance,
        }
        results.append(item)

    # OrgTransactions
    for org in orgs:
        counterparty = ""
        if org.member:
            counterparty = org.member
        item = {
            "table": "Organisation Transaction",
            "created_date": org.created_date,
            "counterparty": counterparty,
            "reference_no": org.reference_no,
            "type": org.type,
            "description": org.description,
            "amount": org.amount,
            "balance": org.balance,
        }
        results.append(item)

    # StripeTransactions
    for stripe_item in stripes:
        counterparty = ""
        if stripe_item.linked_member:
            counterparty = stripe_item.linked_member
        if stripe_item.linked_organisation:
            counterparty = stripe_item.linked_organisation
        item = {
            "table": "Stripe Transaction",
            "created_date": stripe_item.created_date,
            "counterparty": counterparty,
            "reference_no": stripe_item.stripe_reference,
            "type": stripe_item.status,
            "description": stripe_item.description,
            "amount": stripe_item.amount,
            "balance": "",
        }
        results.append(item)

    # Sort by created_date
    results = sorted(results, key=lambda k: k["created_date"])

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="reconciliation.csv"'

    writer = csv.writer(response)
    writer.writerow([f"Generated by {request.user.full_name}", f"Generated on {today}"])
    writer.writerow(
        ["Date range >=", dateformat.format(ref_date_month_earlier, "Y-m-d H:i:s")]
    )
    writer.writerow(["Date range <=", dateformat.format(ref_date, "Y-m-d H:i:s")])
    writer.writerow([""])
    writer.writerow(
        [
            "Date",
            "Table",
            "Counterparty",
            "Reference",
            "Type",
            "Description",
            "Amount",
            "Balance",
        ]
    )

    for result in results:
        writer.writerow(
            [
                dateformat.format(result["created_date"], "Y-m-d H:i:s"),
                result["table"],
                result["counterparty"],
                result["reference_no"],
                result["type"],
                result["description"],
                result["amount"],
                result["balance"],
            ]
        )

    return response


@rbac_check_role("payments.global.view")
def admin_stripe_rec_download_member(request):
    """CSV download of closing member balances just prior to the reference date
    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    # Get the ref date
    ref_date, _ = _admin_stripe_rec_ref_date(request)

    # Get the member balances
    members_balance, members = _get_member_balance_at_date(ref_date)

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="member_balances.csv"'

    writer = csv.writer(response)
    writer.writerow([f"Generated by {request.user.full_name}", f"Generated on {today}"])
    writer.writerow(["Balances prior to", dateformat.format(ref_date, "Y-m-d H:i:s")])

    writer.writerow([""])
    writer.writerow(
        [
            "Member",
            f"{GLOBAL_ORG} Number",
            "Balance",
            "Last Transaction Date",
            "Last Transaction Amount",
            "Last Transaction Description",
        ]
    )

    for member in members:
        writer.writerow(
            [
                member.member.full_name,
                member.member.system_number,
                member.balance,
                dateformat.format(member.created_date, "Y-m-d H:i:s"),
                member.amount,
                member.description,
            ]
        )

    return response


@rbac_check_role("payments.global.view")
def admin_stripe_rec_download_org(request):
    """CSV download of closing organisation balances just prior to the reference date
    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    # Get the ref date
    ref_date, _ = _admin_stripe_rec_ref_date(request)

    # Get the member balances
    org_balance, orgs = _get_org_balance_at_date(ref_date)

    local_dt = timezone.localtime(timezone.now(), TZ)
    today = dateformat.format(local_dt, "Y-m-d H:i:s")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="organisation_balances.csv"'

    writer = csv.writer(response)
    writer.writerow([f"Generated by {request.user.full_name}", f"Generated on {today}"])
    writer.writerow(["Balances prior to", dateformat.format(ref_date, "Y-m-d H:i:s")])

    writer.writerow([""])
    writer.writerow(
        [
            "Organisation",
            f"{GLOBAL_ORG} Org Number",
            "Balance",
            "Last Transaction Date",
            "Last Transaction Amount",
            "Last Transaction Description",
        ]
    )

    for org in orgs:
        writer.writerow(
            [
                org.organisation.name,
                org.organisation.org_id,
                org.balance,
                dateformat.format(org.created_date, "Y-m-d H:i:s"),
                org.amount,
                org.description,
            ]
        )

    return response
