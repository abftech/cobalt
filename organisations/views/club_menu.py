"""
Map

The entry point is club_menu() which loads the page menu.html
Menu.html uses HTMX to load the tab pages e.g. tab_dashboard_htmx()

"""
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from accounts.forms import UnregisteredUserForm
from accounts.models import User, UnregisteredUser
from cobalt.settings import GLOBAL_MPSERVER
from events.models import Congress
from organisations.forms import OrgForm, MembershipTypeForm, OrgDatesForm
from organisations.models import (
    ORGS_RBAC_GROUPS_AND_ROLES,
    Organisation,
    MembershipType,
    MemberMembershipType,
)
from organisations.views.admin import (
    rbac_get_basic_and_advanced,
    get_secretary_from_org_form,
)
from organisations.views.general import (
    get_rbac_model_for_state,
    get_club_data_from_masterpoints_centre,
    compare_form_with_mpc,
)
from payments.core import get_balance_and_recent_trans_org
from rbac.core import (
    rbac_get_group_by_name,
    rbac_get_users_in_group,
    rbac_user_has_role,
    rbac_add_user_to_group,
    rbac_remove_user_from_group,
    rbac_get_admin_group_by_name,
    rbac_remove_admin_user_from_group,
    rbac_get_admin_users_in_group,
    rbac_add_user_to_admin_group,
)
from rbac.models import RBACAdminUserGroup, RBACUserGroup, RBACGroupRole

from rbac.views import rbac_forbidden
from utils.views import masterpoint_query


def _menu_rbac_has_access(club, user):
    """Check if this user has access to this club

    This can be from having rbac rights to this organisation
    or... having state access to the organisation
    or... being a global admin

    Args:
        club(Organisation) - organisation to check
        user(User) - user access to check

    Returns:
        Boolean - True or False for access
        Role (str) - Club role needed if access is denied

    """

    # Check club access
    club_role = f"orgs.org.{club.id}.edit"
    if rbac_user_has_role(user, club_role):
        return True, None

    # Check state access
    rbac_model_for_state = get_rbac_model_for_state(club.state)
    state_role = "orgs.state.%s.edit" % rbac_model_for_state
    if rbac_user_has_role(user, state_role):
        return True, None

    # Check global role
    if rbac_user_has_role(user, "orgs.admin.edit"):
        return True, None

    return False, club_role


def _user_is_uber_admin(club, user):
    """Check if this user has higher level access - state or global"""

    # check if in State group
    rbac_model_for_state = get_rbac_model_for_state(club.state)
    state_role = "orgs.state.%s.edit" % rbac_model_for_state
    if rbac_user_has_role(user, state_role):
        return True

    # Check for global role
    elif rbac_user_has_role(user, "orgs.admin.edit"):
        return True

    return False


def _menu_rbac_advanced_is_admin(club, user):
    """Check if the user is an RBAC admin for this club when using advanced RBAC set up"""

    admin_group = rbac_get_admin_group_by_name(
        f"{club.rbac_admin_name_qualifier}.admin"
    )
    admins = rbac_get_admin_users_in_group(admin_group)

    # Check if in admin group
    if user in admins:
        return True

    # Check for higher level accees
    return _user_is_uber_admin(club, user)


def access_basic(request, club):  # sourcery skip: list-comprehension
    """Do the work for the Access tab on the club menu for basic RBAC."""

    group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.basic")

    # Get users
    users = rbac_get_users_in_group(group)

    for user in users:
        user.hx_post = reverse(
            "organisations:club_admin_access_basic_delete_user_htmx",
            kwargs={"club_id": club.id, "user_id": user.id},
        )

    # Get roles
    roles = []
    for rule in ORGS_RBAC_GROUPS_AND_ROLES:
        roles.append(f"{ORGS_RBAC_GROUPS_AND_ROLES[rule]['description']} {club}")

    return render(
        request,
        "organisations/club_menu/access_basic.html",
        {"club": club, "setup": "basic", "users": users, "roles": roles},
    )


def access_basic_div(request, club):  # sourcery skip: list-comprehension
    """Do the work for the Access tab on the club menu for basic RBAC."""

    group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.basic")

    # Get users
    users = rbac_get_users_in_group(group)

    for user in users:
        user.hx_post = reverse(
            "organisations:club_admin_access_basic_delete_user_htmx",
            kwargs={"club_id": club.id, "user_id": user.id},
        )

    # Get roles
    roles = []
    for rule in ORGS_RBAC_GROUPS_AND_ROLES:
        roles.append(f"{ORGS_RBAC_GROUPS_AND_ROLES[rule]['description']} {club}")

    return render(
        request,
        "organisations/club_menu/access_basic_div_htmx.html",
        {"club": club, "setup": "basic", "users": users, "roles": roles},
    )


def access_advanced(request, club, errors={}):
    """Do the work for the Access tab on the club menu for advanced RBAC."""

    # We have multiple groups to handle so we get a dictionary for users with the role as the key
    user_roles = {}
    admin_list = []

    for rule in ORGS_RBAC_GROUPS_AND_ROLES:

        # get group
        group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.{rule}")

        # Get users
        users = rbac_get_users_in_group(group)
        user_list = []
        for user in users:
            # link for HTMX hx_post to go to
            user.hx_post = reverse(
                "organisations:club_admin_access_advanced_delete_user_htmx",
                kwargs={
                    "club_id": club.id,
                    "user_id": user.id,
                    "group_name_item": rule,
                },
            )
            # unique id for this user and group
            user.delete_id = f"{rule}-{user.id}"

            user_list.append(user)

        desc = f"{ORGS_RBAC_GROUPS_AND_ROLES[rule]['description']}"

        user_roles[rule] = [desc, user_list]

        # Get admins
        admin_group = rbac_get_admin_group_by_name(
            f"{club.rbac_admin_name_qualifier}.admin"
        )
        admins = rbac_get_admin_users_in_group(admin_group)
        admin_list = []
        for admin in admins:
            admin.hx_post = reverse(
                "organisations:access_advanced_delete_admin_htmx",
                kwargs={
                    "club_id": club.id,
                    "user_id": admin.id,
                },
            )
            admin_list.append(admin)

    # Check if this use is an admin (in RBAC admin group or has higher access)
    user_is_admin = _menu_rbac_advanced_is_admin(club, request.user)

    # disable buttons (still show them) if user not admin
    disable_buttons = "" if user_is_admin else "disabled"

    return render(
        request,
        "organisations/club_menu/access_advanced.html",
        {
            "club": club,
            "user_is_admin": user_is_admin,
            "disable_buttons": disable_buttons,
            "user_roles": user_roles,
            "admin_list": admin_list,
            "errors": errors,
        },
    )


@login_required()
def club_menu(request, club_id):
    """Main menu for club administrators to handle things.

    This uses a tabbed navigation panel with each tab providing distinct information.
    We use a different sub function to prepare the information for each tab to keep it clean.

    Args:
        club_id - organisation to view

    Returns:
        HttpResponse - page to edit organisation
    """

    club = get_object_or_404(Organisation, pk=club_id)

    # Check access
    allowed, role = _menu_rbac_has_access(club, request.user)
    if not allowed:
        return rbac_forbidden(request, role)

    # Reduce database calls
    uber_admin = _user_is_uber_admin(club, request.user)

    # Check if we show the finance tab
    show_finance = uber_admin or rbac_user_has_role(
        request.user, f"orgs.org.{club.id}.edit"
    )
    # Check if we show the congress tab
    show_congress = uber_admin or rbac_user_has_role(
        request.user, f"events.org.{club.id}.edit"
    )

    # Check if staff member for other clubs - get all from tree that are like "clubs.generated"
    other_club_ids = (
        RBACGroupRole.objects.filter(group__rbacusergroup__member=request.user)
        .filter(group__name_qualifier__contains="clubs.generated")
        .values("model_id")
        .distinct()
    )
    if len(other_club_ids) > 1:
        other_clubs = Organisation.objects.filter(pk__in=other_club_ids).exclude(
            pk=club.id
        )
    else:
        other_clubs = None

    return render(
        request,
        "organisations/club_menu/menu.html",
        {
            "club": club,
            "show_finance": show_finance,
            "show_congress": show_congress,
            "other_clubs": other_clubs,
        },
    )


def _tab_is_okay(request):
    """Common initial tasks for tabs:
    - get club
    - check RBAC access
    - check this is a post

     Args:
        request: standard request object

    Returns:
        status: Boolean. True - ok to continue, False - not okay
        error_page: HTTPResponse to return if status is False
        club - Organisation - club to use if status is True

    """
    if request.method != "POST":
        return False, HttpResponse("Error"), None

    # Get club
    club_id = request.POST.get("club_id")
    club = get_object_or_404(Organisation, pk=club_id)

    # Check security
    allowed, role = _menu_rbac_has_access(club, request.user)
    if not allowed:
        return False, rbac_forbidden(request, role), None

    return True, None, club


@login_required()
def tab_access_htmx(request):
    """build the access tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Access tab - we have basic or advanced which are very different so use two functions for this
    rbac_basic, rbac_advanced = rbac_get_basic_and_advanced(club)

    if rbac_basic:
        return access_basic(request, club)
    else:
        return access_advanced(request, club)


@login_required()
def tab_dashboard_htmx(request):
    """build the dashboard tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Get members active now
    now = timezone.now()
    member_count = (
        MemberMembershipType.objects.filter(membership_type__organisation=club)
        .filter(start_date__lte=now)
        .filter(Q(end_date__gte=now) | Q(end_date=None))
        .count()
    )

    # Gets members active 28 days ago
    past = timezone.now() - datetime.timedelta(days=28)
    member_count_before = (
        MemberMembershipType.objects.filter(membership_type__organisation=club)
        .filter(start_date__lte=past)
        .filter(Q(end_date__gte=past) | Q(end_date=None))
        .count()
    )

    diff = member_count - member_count_before
    diff_28_days = "No change" if diff == 0 else "{0:+d}".format(diff)
    congress_count = Congress.objects.filter(congress_master__org=club).count()
    staff_count = (
        RBACUserGroup.objects.filter(group__rbacgrouprole__model_id=club.id)
        .filter(group__name_qualifier=club.rbac_name_qualifier)
        .values_list("member")
        .distinct()
        .count()
    )

    return render(
        request,
        "organisations/club_menu/tab_dashboard_htmx.html",
        {
            "club": club,
            "member_count": member_count,
            "congress_count": congress_count,
            "staff_count": staff_count,
            "diff_28_days": diff_28_days,
        },
    )


@login_required()
def tab_comms_htmx(request):
    """build the comms tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    return render(
        request, "organisations/club_menu/tab_comms_htmx.html", {"club": club}
    )


@login_required()
def tab_congress_htmx(request):
    """build the congress tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    congresses = Congress.objects.filter(congress_master__org=club)

    return render(
        request,
        "organisations/club_menu/tab_congress_htmx.html",
        {"club": club, "congresses": congresses},
    )


def get_members_balance(club: Organisation):
    """Get the total balance for members of this club"""

    return 0.0


@login_required()
def tab_finance_htmx(request):
    """build the finance tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    balance, recent_trans = get_balance_and_recent_trans_org(club)

    members_balance = get_members_balance(club)

    return render(
        request,
        "organisations/club_menu/tab_finance_htmx.html",
        {
            "club": club,
            "balance": balance,
            "recent_trans": recent_trans,
            "members_balance": members_balance,
        },
    )


@login_required()
def tab_members_htmx(request):
    """build the members tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

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

    total_members = cobalt_members.count() + unregistered_members.count()

    return render(
        request,
        "organisations/club_menu/tab_members_htmx.html",
        {
            "club": club,
            "cobalt_members": cobalt_members,
            "unregistered_members": unregistered_members,
            "total_members": total_members,
        },
    )


@login_required()
def tab_members_un_reg_edit_htmx(request):
    """Edit unregistered member details"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    un_reg_id = request.POST.get("un_reg_id")
    un_reg = get_object_or_404(UnregisteredUser, pk=un_reg_id)

    user_form = UnregisteredUserForm(instance=un_reg)

    return render(
        request,
        "organisations/club_menu/tab_members_un_reg_edit_htmx.html",
        {"club": club, "un_reg": un_reg, "user_form": user_form},
    )


@login_required()
def tab_forums_htmx(request):
    """build the forums tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    return render(
        request, "organisations/club_menu/tab_forums_htmx.html", {"club": club}
    )


@login_required()
def tab_results_htmx(request):
    """build the results tab in club menu"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    return render(
        request, "organisations/club_menu/tab_results_htmx.html", {"club": club}
    )


@login_required()
def tab_settings_basic_htmx(request):
    """build the settings tab in club menu for editing basic details"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    message = ""

    # The form handles the RBAC checks

    # This is a POST even the first time so look for "save" to see if this really is a form submit
    real_post = "Save" in request.POST

    if not real_post:
        org_form = OrgForm(user=request.user, instance=club)
    else:
        org_form = OrgForm(request.POST, user=request.user, instance=club)

        if org_form.is_valid():
            org = org_form.save(commit=False)
            org.last_updated_by = request.user
            org.last_updated = timezone.localtime()
            org.save()

            # We can't use Django messages as they won't show until the whole page reloads
            message = "Organisation details updated"

    org_form = compare_form_with_mpc(org_form, club)

    # secretary is a bit fiddly so we pass as a separate thing
    secretary_id, secretary_name = get_secretary_from_org_form(org_form)

    # Check if this user is state or global admin - then they can change the State or org_id
    uber_admin = _user_is_uber_admin(club, request.user)

    return render(
        request,
        "organisations/club_menu/tab_settings_basic_htmx.html",
        {
            "club": club,
            "org_form": org_form,
            "secretary_id": secretary_id,
            "secretary_name": secretary_name,
            "uber_admin": uber_admin,
            "message": message,
        },
    )


@login_required()
def tab_settings_basic_reload_htmx(request):
    """Reload data from MPC and return the settings basic tab"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    qry = f"{GLOBAL_MPSERVER}/clubDetails/{club.org_id}"
    data = masterpoint_query(qry)[0]

    club.name = data["ClubName"]
    club.state = data["VenueState"]
    club.postcode = data["VenuePostcode"]
    club.club_email = data["ClubEmail"]
    club.club_website = data["ClubWebsite"]
    club.address1 = data["VenueAddress1"]
    club.address2 = data["VenueAddress2"]
    club.suburb = data["VenueSuburb"]

    club.save()

    return tab_settings_basic_htmx(request)


@login_required()
def tab_settings_general_htmx(request):
    """build the settings tab in club menu for editing general details"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    message = ""

    # This is a POST even the first time so look for "save" to see if this really is a form submit
    real_post = "save" in request.POST

    if not real_post:
        form = OrgDatesForm(instance=club)
    else:
        form = OrgDatesForm(request.POST, instance=club)

        if form.is_valid():
            org = form.save(commit=False)
            org.last_updated_by = request.user
            org.last_updated = timezone.localtime()
            org.save()

            # We can't use Django messages as they won't show until the whole page reloads
            message = "Organisation details updated"

    return render(
        request,
        "organisations/club_menu/tab_settings_general_htmx.html",
        {
            "club": club,
            "form": form,
            "message": message,
        },
    )


@login_required()
def tab_settings_membership_htmx(request):
    """build the settings tab in club menu for editing membership types"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    membership_types = MembershipType.objects.filter(organisation=club)

    return render(
        request,
        "organisations/club_menu/tab_settings_membership_htmx.html",
        {
            "club": club,
            "membership_types": membership_types,
        },
    )


@login_required()
def club_menu_tab_settings_membership_edit_htmx(request):
    """Part of the settings tab for membership types to allow user to edit the membership type

    When a membership type is clicked on, this code is run and returns a form to edit the
    details.
    """

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Get membership type id
    membership_type_id = request.POST.get("membership_type_id")
    membership_type = get_object_or_404(MembershipType, pk=membership_type_id)

    # This is a POST even the first time so look for "save" to see if this really is a form submit
    real_post = "save" in request.POST

    if not real_post:
        form = MembershipTypeForm(instance=membership_type)
    else:
        form = MembershipTypeForm(request.POST, instance=membership_type)

    message = ""

    if form.is_valid():
        updated = form.save(commit=False)
        updated.last_modified_by = request.user
        updated.save()
        message = "Membership Type Updated"

    return render(
        request,
        "organisations/club_menu/tab_settings_membership_edit_htmx.html",
        {
            "club": club,
            "membership_type": membership_type,
            "form": form,
            "message": message,
        },
    )


@login_required()
def club_menu_tab_settings_membership_add_htmx(request):
    """Part of the settings tab for membership types to allow user to add a membership type"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # This is a POST even the first time so look for "save" to see if this really is a form submit
    real_post = "save" in request.POST

    form = MembershipTypeForm(request.POST) if real_post else MembershipTypeForm()
    message = ""

    if form.is_valid():
        membership_type = form.save(commit=False)
        membership_type.last_modified_by = request.user
        membership_type.organisation = club
        membership_type.save()
        #        message = "Membership Type Added"
        return tab_settings_membership_htmx(request)

    return render(
        request,
        "organisations/club_menu/tab_settings_membership_add_htmx.html",
        {
            "club": club,
            "form": form,
            "message": message,
        },
    )


@login_required()
def club_menu_tab_settings_membership_delete_htmx(request):
    """Part of the settings tab for membership types to allow user to delete a membership type"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Get membership type id
    membership_type_id = request.POST.get("membership_type_id")
    membership_type = get_object_or_404(MembershipType, pk=membership_type_id)

    # Check for active members in this membership type
    now = timezone.now()
    if (
        MemberMembershipType.objects.filter(membership_type=membership_type)
        .filter(start_date__lte=now)
        .filter(Q(end_date__gte=now) | Q(end_date=None))
        .exists()
    ):
        return HttpResponse(
            f"<h2 class='text-center'>Cannot Delete {membership_type.name}</h2> "
            f"<h3 class='text-center'>There Are Active Members Here</h3> "
            f"<p class='text-center'>Change members membership types first.</p>."
        )

    # The first time we show a confirmation
    if "delete" not in request.POST:
        return render(
            request,
            "organisations/club_menu/tab_settings_membership_delete_confirm_htmx.html",
            {"membership_type": membership_type},
        )
    else:
        membership_type.delete()

    return tab_settings_membership_htmx(request)


@login_required()
def access_basic_add_user_htmx(request):
    """Add a user to club rbac basic group. Returns HTMX"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Get user
    user_id = request.POST.get("user_id")
    user = get_object_or_404(User, pk=user_id)

    # Get group
    group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.basic")

    # Add user to group
    rbac_add_user_to_group(user, group)

    # All users are admins
    admin_group = rbac_get_admin_group_by_name(
        f"{club.rbac_admin_name_qualifier}.admin"
    )
    rbac_add_user_to_admin_group(user, admin_group)

    return access_basic_div(request, club)


@login_required()
def access_advanced_add_user_htmx(request):
    """Add a user to club rbac advanced group. Returns HTMX"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Get user
    user_id = request.POST.get("user_id")
    user = get_object_or_404(User, pk=user_id)

    # Get group
    group_name_item = request.POST.get("group_name_item")

    group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.{group_name_item}")

    errors = {}
    if RBACUserGroup.objects.filter(group=group, member=user).exists():
        errors[group_name_item] = f"{user.first_name} is already in this group"
    else:
        rbac_add_user_to_group(user, group)

    return access_advanced(request, club, errors)


@login_required()
def access_basic_delete_user_htmx(request, club_id, user_id):
    """Remove a user from club rbac basic group. Returns HTMX"""

    club = get_object_or_404(Organisation, pk=club_id)
    user = get_object_or_404(User, pk=user_id)

    # Check security
    allowed, role = _menu_rbac_has_access(club, request.user)
    if not allowed:
        return rbac_forbidden(request, role)

    group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.basic")
    rbac_remove_user_from_group(user, group)

    # Also remove admin
    admin_group = rbac_get_admin_group_by_name(
        f"{club.rbac_admin_name_qualifier}.admin"
    )
    rbac_remove_admin_user_from_group(user, admin_group)

    return access_basic(request, club)


@login_required()
def access_advanced_delete_user_htmx(request, club_id, user_id, group_name_item):
    """Remove a user from club rbac advanced group. Returns HTMX"""

    club = get_object_or_404(Organisation, pk=club_id)
    user = get_object_or_404(User, pk=user_id)

    # Check if this use is an admin (in RBAC admin group or has higher access)
    if not _menu_rbac_advanced_is_admin(club, request.user):
        return HttpResponse("Access denied")

    group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.{group_name_item}")
    rbac_remove_user_from_group(user, group)

    return access_advanced(request, club)


@login_required()
def access_advanced_delete_admin_htmx(request, club_id, user_id):
    """Remove an admin from club rbac advanced group. Returns HTMX"""

    club = get_object_or_404(Organisation, pk=club_id)
    user = get_object_or_404(User, pk=user_id)

    # Check if this use is an admin (in RBAC admin group or has higher access)
    if not _menu_rbac_advanced_is_admin(club, request.user):
        return HttpResponse("Access denied")

    admin_group = rbac_get_admin_group_by_name(
        f"{club.rbac_admin_name_qualifier}.admin"
    )

    # Don't allow the last admin to be removed
    errors = {}

    if RBACAdminUserGroup.objects.filter(group=admin_group).count() > 1:
        rbac_remove_admin_user_from_group(user, admin_group)
    else:
        errors["admin"] = "Cannot delete the last admin user"

    return access_advanced(request, club, errors)


@login_required()
def access_advanced_add_admin_htmx(request):
    """Add an admin to club rbac advanced group. Returns HTMX"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Check if this use is an admin (in RBAC admin group or has higher access)
    if not _menu_rbac_advanced_is_admin(club, request.user):
        return HttpResponse("Access denied")

    # Get user
    user_id = request.POST.get("user_id")
    user = get_object_or_404(User, pk=user_id)

    admin_group = rbac_get_admin_group_by_name(
        f"{club.rbac_admin_name_qualifier}.admin"
    )

    rbac_add_user_to_admin_group(user, admin_group)

    return access_advanced(request, club)


def club_menu_tab_members_upload_csv_htmx(request):
    """Upload CSV"""

    if request.method == "GET":
        return render(request, "organisations/club_menu/tab_members_htmx.html")
    # if not GET, then proceed
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith(".csv"):
            messages.error(request, "File is not CSV type")
        # return HttpResponseRedirect(reverse("organisations:club_menu_tab_members_upload_csv"))
        # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(
                request,
                "Uploaded file is too big (%.2f MB)."
                % (csv_file.size / (1000 * 1000),),
            )
        # return HttpResponseRedirect(reverse("organisations:club_menu_tab_members_upload_csv"))

        file_data = csv_file.read().decode("utf-8")

        # loop over the lines and save them in db. If error , store as string and then display
        for line in file_data.split("\n"):
            fields = line.split(",")
            system_number = fields[1]
            first_name = fields[5]
            last_name = fields[6]
            email = fields[7]
            print(system_number, first_name, last_name, email)

    except Exception as e:
        messages.error(request, "Unable to upload file. " + repr(e))

    return render(request, "organisations/club_menu/tab_members_csv_htmx.html")


def club_menu_tab_members_import_mpc_htmx(request):
    """Import Data from MPC"""

    status, error_page, club = _tab_is_okay(request)
    if not status:
        return error_page

    # Get members from MPC - we only get hoe club members
    qry = f"{GLOBAL_MPSERVER}/clubMemberList/{club.org_id}"
    club_members = masterpoint_query(qry)

    member_data = [
        {
            "system_number": club_member["ABFNumber"],
            "first_name": club_member["GivenNames"],
            "last_name": club_member["Surname"],
            "email": club_member["EmailAddress"],
        }
        for club_member in club_members
    ]

    added_users, added_unregistered_users = process_member_import(
        club, member_data, request.user, "MPC"
    )

    return HttpResponse(
        f"<p>added users: {added_users}</p><p>added unregistered users: {added_unregistered_users}</p>"
    )


def process_member_import(
    club: Organisation, member_data: list, user: User, origin: str
):
    """Common function to process a list of members"""

    # We have to add them to a membership type
    # TODO: make this a choice field
    default_membership = MembershipType.objects.filter(organisation=club).first()

    # counters
    added_users = 0
    added_unregistered_users = 0

    # loop through members
    for club_member in member_data:

        # See if we have an actual user for this
        user_match = User.objects.filter(
            system_number=club_member["system_number"]
        ).first()

        if user_match:
            added_users += 1
        else:
            added_unregistered_users += 1
            # See if we have an unregistered user already
            un_reg = UnregisteredUser.objects.filter(
                system_number=club_member["system_number"]
            ).first()

            # Add club email - TODO
            if not un_reg:
                # Create a new unregistered user
                UnregisteredUser(
                    system_number=club_member["system_number"],
                    first_name=club_member["first_name"],
                    last_name=club_member["last_name"],
                    email=club_member["email"],
                    origin=origin,
                    last_updated_by=user,
                ).save()

        # Add system number to membership type
        MemberMembershipType(
            membership_type=default_membership,
            system_number=club_member["system_number"],
            last_modified_by=user,
        ).save()

    return added_users, added_unregistered_users
