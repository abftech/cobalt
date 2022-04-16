import csv
import datetime
from copy import copy
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone

import organisations.views.club_menu_tabs.utils
from accounts.accounts_views.api import search_for_user_in_cobalt_and_mpc
from accounts.forms import UnregisteredUserForm
from accounts.models import User, UnregisteredUser
from cobalt.settings import GLOBAL_ORG, GLOBAL_TITLE
from organisations.decorators import check_club_menu_access
from organisations.forms import (
    MemberClubEmailForm,
    UserMembershipForm,
    UnregisteredUserAddForm,
    UnregisteredUserMembershipForm,
)
from organisations.models import (
    MemberMembershipType,
    Organisation,
    MemberClubEmail,
    ClubLog,
    MemberClubTag,
    ClubTag,
    MembershipType,
)
from organisations.views.general import (
    _active_email_for_un_reg,
    get_rbac_model_for_state,
)
from rbac.core import rbac_user_has_role
from post_office.models import Email as PostOfficeEmail

from rbac.views import rbac_forbidden


@check_club_menu_access()
def list_htmx(request: HttpRequest, club: Organisation, message: str = None):
    """build the members tab in club menu"""

    # Get System Numbers for All Members
    now = timezone.now()
    club_system_numbers = (
        MemberMembershipType.objects.filter(membership_type__organisation=club)
        .filter(start_date__lte=now)
        .filter(Q(end_date__gte=now) | Q(end_date=None))
        .values("system_number")
    )

    # Get real members
    cobalt_members = User.objects.filter(
        system_number__in=club_system_numbers
    ).order_by("last_name")

    # Get unregistered
    unregistered_members = UnregisteredUser.objects.filter(
        system_number__in=club_system_numbers
    ).order_by("last_name")

    # combine outputs
    members = list(chain(cobalt_members, unregistered_members))

    total_members = cobalt_members.count() + unregistered_members.count()

    # Check level of access
    member_admin = rbac_user_has_role(request.user, f"orgs.members.{club.id}.edit")

    return render(
        request,
        "organisations/club_menu/members/list_htmx.html",
        {
            "club": club,
            "members": members,
            "total_members": total_members,
            "message": message,
            "member_admin": member_admin,
        },
    )


@check_club_menu_access()
def add_htmx(request, club):
    """Add sub menu"""

    total_members = organisations.views.club_menu_tabs.utils._member_count(club)

    # Check level of access
    member_admin = rbac_user_has_role(request.user, f"orgs.members.{club.id}.edit")

    return render(
        request,
        "organisations/club_menu/members/add_menu_htmx.html",
        {
            "club": club,
            "total_members": total_members,
            "member_admin": member_admin,
        },
    )


@check_club_menu_access()
def reports_htmx(request, club):
    """Reports sub menu"""

    # Check level of access
    member_admin = rbac_user_has_role(request.user, f"orgs.members.{club.id}.edit")

    return render(
        request,
        "organisations/club_menu/members/reports_htmx.html",
        {
            "club": club,
            "member_admin": member_admin,
        },
    )


@login_required()
def report_all_csv(request, club_id):
    """CSV of all members. We can't use the decorator as I can't get HTMX to treat this as a CSV"""

    # Get all ABF Numbers for members

    club = get_object_or_404(Organisation, pk=club_id)

    # Check for club level access - most common
    club_role = f"orgs.members.{club.id}.edit"
    if not rbac_user_has_role(request.user, club_role):

        # Check for state level access or global
        rbac_model_for_state = get_rbac_model_for_state(club.state)
        state_role = "orgs.state.%s.edit" % rbac_model_for_state
        if not rbac_user_has_role(request.user, state_role) and not rbac_user_has_role(
            request.user, "orgs.admin.edit"
        ):
            return rbac_forbidden(request, club_role)

    now = timezone.now()
    club_members = (
        MemberMembershipType.objects.filter(start_date__lte=now)
        .filter(Q(end_date__gte=now) | Q(end_date=None))
        .filter(membership_type__organisation=club)
    ).values_list("system_number")

    # Get proper users
    users = User.objects.filter(system_number__in=club_members)

    # Get un reg users
    un_regs = UnregisteredUser.objects.filter(system_number__in=club_members)

    # Get local emails (if set) and turn into a dictionary
    club_emails = MemberClubEmail.objects.filter(system_number__in=club_members)
    club_emails_dict = {}
    for club_email in club_emails:
        club_emails_dict[club_email.system_number] = club_email.email

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="members.csv"'

    writer = csv.writer(response)
    writer.writerow([club.name, f"Downloaded by {request.user.full_name}", now])
    writer.writerow(
        [
            f"{GLOBAL_ORG} Number",
            "First Name",
            "Last Name",
            "Email",
            "Email Source",
            f"{GLOBAL_TITLE} User Type",
            "Origin",
        ]
    )

    for user in users:
        writer.writerow(
            [
                user.system_number,
                user.first_name,
                user.last_name,
                user.email,
                "User",
                "Registered",
                "Self-registered",
            ]
        )

    for un_reg in un_regs:

        email = un_reg.email
        email_source = "Unregistered user"
        if un_reg.system_number in club_emails_dict:
            email = club_emails_dict[un_reg.system_number]
            email_source = "Club specific email"

        writer.writerow(
            [
                un_reg.system_number,
                un_reg.first_name,
                un_reg.last_name,
                email,
                email_source,
                "Unregistered",
                un_reg.origin,
            ]
        )

    return response


def _cancel_membership(request, club, system_number):
    """Common function to cancel membership"""

    # Memberships are coming later. For now we treat as basically binary - they start on the date they are
    # entered and we assume only one without checking
    now = timezone.now()
    memberships = (
        MemberMembershipType.objects.filter(start_date__lte=now)
        .filter(Q(end_date__gte=now) | Q(end_date=None))
        .filter(system_number=system_number)
    )

    # Should only be one but not enforced at database level so close any that match to be safe
    for membership in memberships:
        membership.last_modified_by = request.user
        membership.termination_reason = "Cancelled by Club"
        membership.end_date = now - datetime.timedelta(days=1)
        membership.save()

        ClubLog(
            organisation=club,
            actor=request.user,
            action=f"Cancelled membership for {system_number}",
        ).save()


@check_club_menu_access(check_members=True)
def delete_un_reg_htmx(request, club):
    """Remove an unregistered user from club membership"""

    un_reg = get_object_or_404(UnregisteredUser, pk=request.POST.get("un_reg_id"))
    _cancel_membership(request, club, un_reg.system_number)

    return list_htmx(request, f"{un_reg.full_name} membership deleted.")


@check_club_menu_access(check_members=True)
def delete_member_htmx(request, club):
    """Remove a registered user from club membership"""

    print("member_id:", request.POST.get("member_id"))

    member = get_object_or_404(User, pk=request.POST.get("member_id"))
    _cancel_membership(request, club, member.system_number)

    return list_htmx(request, f"{member.full_name} membership deleted.")


def _un_reg_edit_htmx_process_form(
    request, un_reg, club, membership, user_form, club_email_form, club_membership_form
):
    """Sub process to handle form for un_reg_edit_htmx"""

    # Assume the worst
    message = "Errors found on Form"

    if user_form.is_valid() and club_membership_form.is_valid():
        new_un_reg = user_form.save()
        if club_membership_form.changed_data:
            membership.home_club = club_membership_form.cleaned_data["home_club"]
            membership_type = MembershipType.objects.get(
                pk=club_membership_form.cleaned_data["membership_type"]
            )
            membership.membership_type = membership_type
            membership.save()

        message = "Data Saved"
        ClubLog(
            organisation=club,
            actor=request.user,
            action=f"Updated details for {new_un_reg}",
        ).save()

    if club_email_form.is_valid():
        club_email = club_email_form.cleaned_data["email"]
        club_email_entry, _ = MemberClubEmail.objects.get_or_create(
            organisation=club, system_number=un_reg.system_number
        )
        club_email_entry.email = club_email
        club_email_entry.save()
        message = "Data Saved"
        ClubLog(
            organisation=club,
            actor=request.user,
            action=f"Updated club email address for {un_reg}",
        ).save()

    return message, un_reg


def _un_reg_edit_htmx_common(
    request,
    club,
    un_reg,
    message,
    user_form,
    club_email_form,
    club_membership_form,
    member_details,
):
    """Common part of editing un registered user, used whether form was filled in or not"""

    member_tags = MemberClubTag.objects.prefetch_related("club_tag").filter(
        club_tag__organisation=club, system_number=un_reg.system_number
    )
    used_tags = member_tags.values("club_tag__tag_name")
    available_tags = ClubTag.objects.filter(organisation=club).exclude(
        tag_name__in=used_tags
    )

    # Get recent emails if allowed
    if rbac_user_has_role(
        request.user, f"notifications.orgcomms.{club.id}.view"
    ) or rbac_user_has_role(request.user, "orgs.admin.edit"):
        emails = PostOfficeEmail.objects.filter(
            to=[_active_email_for_un_reg(un_reg, club)]
        ).order_by("-pk")[:20]
    else:
        emails = None

    return render(
        request,
        "organisations/club_menu/members/edit_un_reg_htmx.html",
        {
            "club": club,
            "un_reg": un_reg,
            "user_form": user_form,
            "club_email_form": club_email_form,
            "club_membership_form": club_membership_form,
            "member_details": member_details,
            "member_tags": member_tags,
            "available_tags": available_tags,
            "hx_delete": reverse(
                "organisations:club_menu_tab_member_delete_un_reg_htmx"
            ),
            "hx_args": f"club_id:{club.id},un_reg_id:{un_reg.id}",
            "message": message,
            "emails": emails,
        },
    )


@check_club_menu_access(check_members=True)
def un_reg_edit_htmx(request, club):
    """Edit unregistered member details"""

    un_reg_id = request.POST.get("un_reg_id")
    un_reg = get_object_or_404(UnregisteredUser, pk=un_reg_id)

    member_details = (
        MemberMembershipType.objects.active()
        .filter(system_number=un_reg.system_number)
        .first()
    )
    membership = (
        MemberMembershipType.objects.active()
        .filter(system_number=un_reg.system_number)
        .first()
    )
    message = ""

    if "save" in request.POST:
        # We got form data - process it
        user_form = UnregisteredUserForm(request.POST, instance=un_reg)
        club_email_form = MemberClubEmailForm(request.POST, prefix="club")
        club_membership_form = UnregisteredUserMembershipForm(
            request.POST, club=club, system_number=un_reg.system_number, prefix="member"
        )
        message, un_reg = _un_reg_edit_htmx_process_form(
            request,
            un_reg,
            club,
            membership,
            user_form,
            club_email_form,
            club_membership_form,
        )

    else:
        # No form data so build up what we need to show user
        club_email_entry = MemberClubEmail.objects.filter(
            organisation=club, system_number=un_reg.system_number
        ).first()
        user_form = UnregisteredUserForm(instance=un_reg)
        club_email_form = MemberClubEmailForm(prefix="club")
        club_membership_form = UnregisteredUserMembershipForm(
            club=club, system_number=un_reg.system_number, prefix="member"
        )

        # Set initial values for membership form
        club_membership_form.initial["home_club"] = membership.home_club
        club_membership_form.initial["membership_type"] = membership.membership_type_id

        # Set initial value for email if record exists
        if club_email_entry:
            club_email_form.initial["email"] = club_email_entry.email

    # Common parts
    return _un_reg_edit_htmx_common(
        request,
        club,
        un_reg,
        message,
        user_form,
        club_email_form,
        club_membership_form,
        member_details,
    )


@check_club_menu_access(check_members=True)
def add_member_htmx(request, club):
    """Add a club member manually. This is called by the add_any page and return the list page.
    This shouldn't get errors so we don't return a form, we just use the message field if
    we do get an error and return the list view.
    """

    message = ""

    form = UserMembershipForm(request.POST, club=club)

    print(form)

    if form.is_valid():
        print("inside")
        system_number = int(form.cleaned_data["system_number"])
        membership_type_id = form.cleaned_data["membership_type"]
        home_club = form.cleaned_data["home_club"]
        #   send_welcome_pack = form.cleaned_data["send_welcome_pack"]

        print(system_number)

        member = User.objects.filter(system_number=system_number).first()
        print(member)
        membership_type = MembershipType(pk=membership_type_id)

        if (
            MemberMembershipType.objects.active()
            .filter(
                system_number=member.system_number,
                membership_type__organisation=club,
            )
            .exists()
        ):
            # shouldn't happen, but just in case
            message = f"{member.full_name} is already a member of this club"
        else:
            MemberMembershipType(
                system_number=member.system_number,
                membership_type=membership_type,
                last_modified_by=request.user,
                home_club=home_club,
            ).save()
            message = f"{member.full_name} added as a member"
            ClubLog(
                organisation=club,
                actor=request.user,
                action=f"Added member {member}",
            ).save()
            form = UserMembershipForm(club=club)
    else:
        print(form.errors)

    return list_htmx(request, message)


@check_club_menu_access(check_members=True)
def add_any_member_htmx(request, club):
    """Add a club member manually"""

    member_form = UserMembershipForm(club=club)
    un_reg_form = UnregisteredUserAddForm(club=club)

    return render(
        request,
        "organisations/club_menu/members/add_any_member_htmx.html",
        {"club": club, "member_form": member_form, "un_reg_form": un_reg_form},
    )


@login_required()
def add_member_search_htmx(request):
    """Search function for adding a member (registered, unregistered or from MPC"""

    first_name_search = request.POST.get("member_first_name_search")
    last_name_search = request.POST.get("member_last_name_search")

    # if there is nothing to search for, don't search
    if not first_name_search and not last_name_search:
        return HttpResponse()

    user_list, is_more = search_for_user_in_cobalt_and_mpc(
        first_name_search, last_name_search
    )

    # Now highlight users who are already club members
    user_list_system_numbers = [user["system_number"] for user in user_list]

    member_list = (
        MemberMembershipType.objects.filter(system_number__in=user_list_system_numbers)
        .filter(termination_reason=None)
        .values_list("system_number", flat=True)
    )

    for user in user_list:
        if user["system_number"] in member_list:
            user["source"] = "member"

    return render(
        request,
        "organisations/club_menu/members/member_search_results_htmx.html",
        {"user_list": user_list, "is_more": is_more},
    )


@check_club_menu_access(check_members=True)
def edit_member_htmx(request, club):
    """Edit a club member manually"""

    message = ""

    member_id = request.POST.get("member")
    member = get_object_or_404(User, pk=member_id)

    # Look for save as all requests are posts
    if "save" in request.POST:
        form = UserMembershipForm(request.POST, club=club)

        if form.is_valid():

            # Get details
            membership_type_id = form.cleaned_data["membership_type"]
            membership_type = get_object_or_404(MembershipType, pk=membership_type_id)
            home_club = form.cleaned_data["home_club"]

            # Get the member membership objects
            member_membership = (
                MemberMembershipType.objects.active()
                .filter(system_number=member.system_number)
                .filter(membership_type__organisation=club)
                .first()
            )

            # Update and save
            member_membership.membership_type = membership_type
            member_membership.home_club = home_club
            member_membership.save()
            message = f"{member.full_name} updated"
            ClubLog(
                organisation=club,
                actor=request.user,
                action=f"Edited details for member {member}",
            ).save()
            return list_htmx(request, message)

        else:
            print(form.errors)
    else:
        member_membership = (
            MemberMembershipType.objects.active()
            .filter(system_number=member.system_number)
            .filter(membership_type__organisation=club)
            .first()
        )
        initial = {
            "member": member.id,
            "membership_type": member_membership.membership_type.id,
            "home_club": member_membership.home_club,
        }
        form = UserMembershipForm(club=club)
        form.initial = initial

    hx_delete = reverse("organisations:club_menu_tab_member_delete_member_htmx")
    hx_vars = f"club_id:{club.id},member_id:{member.id}"

    member_tags = MemberClubTag.objects.prefetch_related("club_tag").filter(
        club_tag__organisation=club, system_number=member.system_number
    )
    used_tags = member_tags.values("club_tag__tag_name")
    available_tags = ClubTag.objects.filter(organisation=club).exclude(
        tag_name__in=used_tags
    )

    # Get recent emails too
    if rbac_user_has_role(
        request.user, f"notifications.orgcomms.{club.id}.view"
    ) or rbac_user_has_role(request.user, "orgs.admin.edit"):
        emails = PostOfficeEmail.objects.filter(to=[member.email]).order_by("-pk")[:20]
    else:
        emails = None

    return render(
        request,
        "organisations/club_menu/members/edit_member_htmx.html",
        {
            "club": club,
            "form": form,
            "member": member,
            "message": message,
            "hx_delete": hx_delete,
            "hx_vars": hx_vars,
            "member_tags": member_tags,
            "available_tags": available_tags,
            "emails": emails,
        },
    )


@check_club_menu_access(check_members=True)
def add_un_reg_htmx(request, club):
    """Add a club unregistered user manually. This is called by the add_any page and return the list page.
    This shouldn't get errors so we don't return a form, we just use the message field if
    we do get an error and return the list view.
    """

    message = ""

    form = UnregisteredUserAddForm(request.POST, club=club)

    if form.is_valid():
        # User may already be registered, the form will allow this
        if UnregisteredUser.objects.filter(
            system_number=form.cleaned_data["system_number"],
        ).exists():
            message = "User already existed."  # don't change the fields
        else:
            UnregisteredUser(
                system_number=form.cleaned_data["system_number"],
                last_updated_by=request.user,
                last_name=form.cleaned_data["last_name"],
                first_name=form.cleaned_data["first_name"],
                email=form.cleaned_data["mpc_email"],
                origin="Manual",
                added_by_club=club,
            ).save()
            ClubLog(
                organisation=club,
                actor=request.user,
                action=f"Added un-registered user {form.cleaned_data['first_name']} {form.cleaned_data['last_name']}",
            ).save()
            message = "User added."

        # Add to club
        if (
            MemberMembershipType.objects.active()
            .filter(
                system_number=form.cleaned_data["system_number"],
                membership_type__organisation=club,
            )
            .exists()
        ):
            message += " Already a member of club."
        else:
            MemberMembershipType.objects.get_or_create(
                system_number=form.cleaned_data["system_number"],
                membership_type_id=form.cleaned_data["membership_type"],
                home_club=form.cleaned_data["home_club"],
                last_modified_by=request.user,
            )
            message += " Club membership added."

        # Add email
        club_email = form.cleaned_data["club_email"]
        if club_email:
            club_email_entry, _ = MemberClubEmail.objects.get_or_create(
                organisation=club, system_number=form.cleaned_data["system_number"]
            )
            club_email_entry.email = club_email
            club_email_entry.save()
            ClubLog(
                organisation=club,
                actor=request.user,
                action=f"Added club specific email for {form.cleaned_data['system_number']}",
            ).save()

            message += " Club specific email added."

    # club is added to the call by the decorator
    return list_htmx(request, message)
