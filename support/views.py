import contextlib
import json
from itertools import chain

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from accounts.models import User, UnregisteredUser
from cobalt.settings import (
    COBALT_HOSTNAME,
    RECAPTCHA_SITE_KEY,
    RECAPTCHA_SECRET_KEY,
)
from events.models import Congress
from forums.models import Post, Forum
from organisations.models import Organisation, MemberClubDetails
from payments.models import MemberTransaction
from rbac.core import rbac_user_has_role
from utils.utils import cobalt_paginator
from .forms import (
    HelpdeskLoggedInContactForm,
    HelpdeskLoggedOutContactForm,
)
from .helpdesk import notify_user_new_ticket_by_form, notify_group_new_ticket


@login_required
def home(request):

    helpdesk = bool(rbac_user_has_role(request.user, "support.helpdesk.view"))
    return render(request, "support/general/home.html", {"helpdesk": helpdesk})


@login_required
def admin(request):

    return render(request, "support/general/home_admin.html")


def cookies(request):
    return render(request, "support/general/cookies.html")


def cookies_logged_out(request):
    return render(request, "support/general/cookies_logged_out.html")


def guidelines(request):
    return render(request, "support/general/guidelines.html")


def acceptable_use(request):
    return render(request, "support/general/acceptable_use.html")


def acceptable_use_logged_out(request):
    return render(request, "support/general/acceptable_use_logged_out.html")


def non_production_email_changer(request):
    """Only for test systems - changes email address of all users"""

    if not request.user.is_superuser:
        raise SuspiciousOperation("This is only available for admin users.")

    if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
        raise SuspiciousOperation(
            "Not for use in production. This cannot be used in a production system."
        )

    all_users = User.objects.all()

    if request.method == "POST":
        new_email = request.POST["new_email"]
        for user in all_users:
            user.email = new_email
            user.save()

        count = all_users.count()
        messages.success(
            request,
            f"{count} users updated.",
            extra_tags="cobalt-message-success",
        )

    return render(
        request,
        "support/development/non_production_email_changer.html",
        {"all_users": all_users},
    )


@login_required()
def contact_logged_in(request):
    """Contact form for logged in users"""

    form = HelpdeskLoggedInContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save()
        notify_user_new_ticket_by_form(request, ticket)
        notify_group_new_ticket(request, ticket)

        messages.success(
            request,
            "Helpdesk ticket logged. You will be informed of progress via email.",
            extra_tags="cobalt-message-success",
        )

        return redirect("support:support")

    return render(
        request,
        "support/contact/contact_logged_in.html",
        {
            "form": form,
        },
    )


def contact_logged_out(request):
    """Contact form for logged out users"""

    form = HelpdeskLoggedOutContactForm(request.POST or None)
    is_human = True  # Innocent until proven guilty

    if request.method == "POST" and form.is_valid():

        # Check with Google for status of recaptcha request
        recaptcha_token = request.POST.get("g-recaptcha-response")
        data = {"response": recaptcha_token, "secret": RECAPTCHA_SECRET_KEY}
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify", data=data
        )
        result_json = resp.json()

        is_human = bool(result_json.get("success"))

        if is_human:

            ticket = form.save()
            notify_user_new_ticket_by_form(request, ticket)
            notify_group_new_ticket(request, ticket)

            messages.add_message(
                request,
                messages.INFO,
                "Helpdesk ticket logged. You will be informed of progress via email.",
            )

            return redirect("/")

    return render(
        request,
        "support/contact/contact_logged_out.html",
        {
            "form": form,
            "site_key": RECAPTCHA_SITE_KEY,
            "is_human": is_human,
        },
    )


@login_required
@csrf_exempt
def browser_errors(request):
    """receive errors from browser code and notify support"""

    # Log to stdout only - emails disabled as too much noise from old browser

    if request.method == "POST":
        try:
            data = request.POST.get("data", None)
            if data:
                errors = json.loads(data)
                print(
                    f"Error from browser ignored: {errors['message']} User: {request.user}"
                )

        except Exception as err:
            print(err)

    return HttpResponse("ok")


def _add_memberships_to_queryset(queryset, email_admin=False):
    """augments the queryset with membership data. Works for User or UnregisteredUser"""

    # Get system numbers
    system_numbers = queryset.values_list("system_number")

    # Get matching member_club_detail records - and also load the club info
    member_club_details = (
        MemberClubDetails.objects.filter(system_number__in=system_numbers)
        .order_by("club", "pk")
        .distinct("club")
        .select_related("club")
    )

    # Hide contacts from non-admins, they are private records for clubs only
    if email_admin:
        member_club_details = member_club_details.filter(
            membership_status__in=["CUR", "DUE", "CON"]
        )
    else:
        member_club_details = member_club_details.filter(
            membership_status__in=["CUR", "DUE"]
        )

    # Turn into a dictionary
    lookup = {}
    for item in member_club_details:
        if item.system_number not in lookup:
            lookup[item.system_number] = []
        lookup[item.system_number].append(item)

    # Append to queryset
    for item in queryset:
        try:
            item.member_club_details = lookup[item.system_number]
        except KeyError:
            print(f"Key error looking up {item.system_number}")
    return queryset


def _global_search_people(request, query, searchparams, include_people):
    """sub of global_search to handle people (Users, Unregistered users and contacts)"""

    if not include_people:
        return [], searchparams

    # If this user is an email admin, then we include contacts
    email_admin = bool(rbac_user_has_role(request.user, "notifications.admin.view"))

    # Handle splitting name in to first and second
    if query.find(" ") >= 0:
        first_name_search = query.split(" ")[0]
        last_name_search = " ".join(query.split(" ")[1:])
        q_string = Q(first_name__icontains=first_name_search) & Q(
            last_name__icontains=last_name_search
        )
    else:
        first_name_search = query
        last_name_search = query
        q_string = (
            Q(first_name__icontains=first_name_search)
            | Q(last_name__icontains=last_name_search)
            | Q(system_number__icontains=query)
        )

    registered = User.objects.filter(q_string)

    # Unregistered users holds both unregistered users and contacts who have fake system_numbers assigned
    unregistered = UnregisteredUser.all_objects.filter(q_string)

    # Don't include contacts (have internal system numbers) unless an admin
    if not email_admin:
        unregistered = unregistered.exclude(internal_system_number=True)

    # Augment with membership data
    registered_with_memberships = _add_memberships_to_queryset(registered, email_admin)
    unregistered_with_memberships = _add_memberships_to_queryset(
        unregistered, email_admin
    )

    data = list(chain(registered_with_memberships, unregistered_with_memberships))

    searchparams += "include_people=1&"

    return data, searchparams


@login_required
def global_search(request):
    """This handles the search bar that appears on every page. Also gets called from the search panel that
    we show if a search is performed, to allow the user to reduce the range of the search
    """

    query = request.POST.get("search_string") or request.GET.get("search_string")
    include_people = request.POST.get("include_people") or request.GET.get(
        "include_people"
    )
    include_forums = request.POST.get("include_forums") or request.GET.get(
        "include_forums"
    )
    include_posts = request.POST.get("include_posts") or request.GET.get(
        "include_posts"
    )
    include_events = request.POST.get("include_events") or request.GET.get(
        "include_events"
    )
    include_payments = request.POST.get("include_payments") or request.GET.get(
        "include_payments"
    )
    include_orgs = request.POST.get("include_orgs") or request.GET.get("include_orgs")

    searchparams = ""

    if query:  # don't search if no search string

        searchparams = f"search_string={query.replace(' ', '%20')}&"

        # Users
        people, searchparams = _global_search_people(
            request, query, searchparams, include_people
        )

        # Posts
        if include_posts:
            posts = Post.objects.filter(title__icontains=query)
            searchparams += "include_posts=1&"
        else:
            posts = []

        # Forums
        if include_forums:
            forums = Forum.objects.filter(title__icontains=query)
            searchparams += "include_forums=1&"
        else:
            forums = []

        # Events
        if include_events:
            events = Congress.objects.filter(name__icontains=query)
            searchparams += "include_events=1&"
        else:
            events = []

        # payments
        if include_payments:
            payments = MemberTransaction.objects.filter(
                description__icontains=query, member=request.user
            )
            searchparams += "include_payments=1&"
        else:
            payments = []

        # orgs
        if include_orgs:
            orgs = Organisation.objects.filter(name__icontains=query)
            searchparams += "include_orgs=1&"
        else:
            orgs = []

        # combine outputs
        results = list(chain(people, posts, forums, events, payments, orgs))

        # create paginator
        things = cobalt_paginator(request, results)

    else:  # no search string provided

        things = []

    return render(
        request,
        "support/general/search.html",
        {
            "things": things,
            "search_string": query,
            "include_people": include_people,
            "include_forums": include_forums,
            "include_posts": include_posts,
            "include_events": include_events,
            "include_payments": include_payments,
            "include_orgs": include_orgs,
            "searchparams": searchparams,
        },
    )
