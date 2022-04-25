from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

from accounts.models import User
from club_sessions.club_sessions_views.admin import add_club_session_defaults
from cobalt.settings import ABF_USER
from organisations.forms import OrgForm
from organisations.models import (
    Organisation,
    ORGS_RBAC_GROUPS_AND_ROLES,
    MembershipType,
    ClubLog,
)
from organisations.views import general
from rbac.core import (
    rbac_user_has_role,
    rbac_get_group_by_name,
    rbac_create_group,
    rbac_add_user_to_group,
    rbac_add_role_to_group,
    rbac_create_admin_group,
    rbac_add_user_to_admin_group,
    rbac_admin_add_tree_to_group,
    rbac_get_users_in_group_by_name,
    rbac_delete_group_by_name,
    rbac_get_users_in_group,
    rbac_delete_group,
    rbac_user_has_admin_tree_access,
    rbac_user_has_any_model,
)
from rbac.models import RBACGroupRole
from rbac.views import rbac_forbidden


def get_secretary_from_org_form(org_form):
    """on org form we have a secretary for the club. We use the Cobalt user search for this so extract
    details from form"""

    secretary_id = org_form["secretary"].value()
    if secretary_id:
        secretary_name = User.objects.filter(pk=secretary_id).first()
    else:
        secretary_name = ""

    return secretary_id, secretary_name


def add_club_defaults(club: Organisation):
    """Add sensible default values when we create a new club"""

    # Use basic RBAC
    _admin_club_rbac_add_basic_sub(club)

    # Membership Types
    system = User.objects.get(pk=ABF_USER)

    MembershipType(
        organisation=club,
        name="Standard",
        description="Normal membership type for standard members.\n\nThis is the default membership type. "
        "You can edit the values to suit your club. \n\nThere is a membership fee as well as a "
        "reduced fee which takes effect part way through the year. Use the General tab to set "
        "when membership is due and when the reduced fee will start to apply.\n\n"
        "The checkboxes are generally used for special memberships such as Life Members.",
        annual_fee=50,
        part_year_fee=25,
        last_modified_by=system,
        is_default=True,
    ).save()

    MembershipType(
        organisation=club,
        name="Life Member",
        description="Life Members do not pay annual subscriptions or table fees for club sessions.",
        annual_fee=0,
        does_not_renew=True,
        does_not_pay_session_fees=True,
        last_modified_by=system,
    ).save()

    MembershipType(
        organisation=club,
        name="Youth",
        description="Youth players usually pay a reduced membership fee as well as lower table fees.",
        annual_fee=25,
        does_not_renew=True,
        does_not_pay_session_fees=True,
        last_modified_by=system,
    ).save()

    # Add defaults for club sessions too
    add_club_session_defaults(club)

    # log it
    system = User.objects.get(pk=ABF_USER)

    ClubLog(
        organisation=club,
        actor=system,
        action="Initial defaults set up",
    ).save()


@login_required()
def admin_add_club(request):
    """Add a club to the system. For State or ABF Administrators

    NOTE: For now the club must be defined in the Masterpoints Centre already

    """
    # TODO: Get rid of higher up edit org function and replace with this

    # The form handles the RBAC checks
    form = OrgForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        # Validate here rather in form as form is shared with edit function
        if Organisation.objects.filter(org_id=form.cleaned_data["org_id"]).exists():
            form.add_error("org_id", "This organisation is already set up")
        else:
            org = form.save(commit=False)
            org.last_updated_by = request.user
            org.last_updated = timezone.localtime()
            org.type = "Club"
            org.save()
            add_club_defaults(org)
            messages.success(
                request,
                f"{org.name} created with standard defaults.",
                extra_tags="cobalt-message-success",
            )
            return redirect("organisations:club_menu", club_id=org.id)

    secretary_id, secretary_name = get_secretary_from_org_form(form)

    return render(
        request,
        "organisations/admin_add_club.html",
        {"form": form, "secretary_id": secretary_id, "secretary_name": secretary_name},
    )


@login_required()
def admin_list_clubs(request):
    """List Clubs in the system. For State or ABF Administrators"""

    clubs = Organisation.objects.filter(type="Club").order_by("state", "name")

    # Check roles so we only show clubs user can edit

    # Global admin - gets everything
    if rbac_user_has_role(request.user, "orgs.admin.edit"):
        for club in clubs:
            club.user_can_edit = True

    else:
        # State admin (could have clubs too)
        states_rbac = (
            RBACGroupRole.objects.filter(app="orgs", model="state")
            .filter(group__rbacusergroup__member=request.user)
            .values("model_id")
        )
        if states_rbac:
            states = Organisation.objects.filter(pk__in=states_rbac).values_list(
                "state", flat=True
            )
            for club in clubs:
                if club.state in states:
                    club.user_can_edit = True

        # individual clubs - goes on top of state access (if any)
        clubs_rbac = (
            RBACGroupRole.objects.filter(app="orgs", model="org")
            .filter(Q(action="edit") | Q(action="all"))
            .filter(group__rbacusergroup__member=request.user)
            .values_list("model_id", flat=True)
        )

        for club in clubs:
            if club.id in clubs_rbac:
                club.user_can_edit = True

    # Group by State
    grouped_by_state = {}

    for club in clubs:
        if club.state in grouped_by_state:
            grouped_by_state[club.state].append(club)
        else:
            grouped_by_state[club.state] = [club]

    return render(
        request,
        "organisations/admin_list_clubs.html",
        {"grouped_by_state": grouped_by_state},
    )


def _rbac_user_has_admin(club, user):
    """Check if this user has access to do rbac admin for this club"""

    # First check individual role
    user_role = f"orgs.org.{club.id}.view"

    if rbac_user_has_role(user, user_role):
        # User has the right role, but if RBAC Advanced, also needs the admin tree permissions
        _, advanced = rbac_get_basic_and_advanced(club)

        # If not advanced then anyone can administer this,
        # if advanced then also need the admin role - assume conveners always there
        if not advanced or rbac_user_has_admin_tree_access(
            user, f"{club.rbac_name_qualifier}.conveners"
        ):
            return True, None

    # Not individual, try higher up access

    # Get model id for this state
    rbac_model_for_state = general.get_rbac_model_for_state(club.state)

    # Check admin access
    role = "orgs.state.%s.edit" % rbac_model_for_state
    if not (
        rbac_user_has_role(user, role) or rbac_user_has_role(user, "orgs.admin.edit")
    ):
        return False, user_role

    return True, None


def rbac_get_basic_and_advanced(club):
    """Get the setup for this club"""

    # Basic is e.g. rbac.orgs.clubs.generated.nsw.34.basic (we can't use the club name as it might change, use pk)
    rbac_basic = rbac_get_group_by_name(
        "rbac.orgs.clubs.generated.%s.%s.basic" % (club.state.lower(), club.id)
    )

    # Advanced has a few groups e.g. rbac.orgs.clubs.generated.nsw.34.conveners
    # Assume conveners will always work
    rbac_advanced = rbac_get_group_by_name(
        "rbac.orgs.clubs.generated.%s.%s.conveners" % (club.state.lower(), club.id)
    )

    return bool(rbac_basic), bool(rbac_advanced)


@login_required()
def admin_club_rbac(request, club_id):
    """Manage RBAC basic set up for a Club

    This doesn't control who gets access - clubs can do that themselves, this controls whether it is basic
    or advanced RBAC configuration. It is the RBAC structure, not the content.

    """

    # Get club
    club = get_object_or_404(Organisation, pk=club_id)

    has_access, role = _rbac_user_has_admin(club, request.user)
    if not has_access:
        return rbac_forbidden(request, role)

    # Check rbac setup
    rbac_basic, rbac_advanced = rbac_get_basic_and_advanced(club)

    error = ""
    new_setup = False

    if rbac_advanced and rbac_basic:
        error = "Error: This club is set up with both simple and advanced RBAC. Contact Support."

    if not rbac_advanced and not rbac_basic:
        error = "RBAC not set up yet."
        new_setup = True

    return render(
        request,
        "organisations/admin_club_rbac.html",
        {
            "club": club,
            "new_setup": new_setup,
            "rbac_basic": rbac_basic,
            "rbac_advanced": rbac_advanced,
            "error": error,
        },
    )


def _admin_club_rbac_add_basic_sub(club):
    """low level steps to add rbac basic for club"""

    # Create group
    group = rbac_create_group(
        name_qualifier=club.rbac_name_qualifier,
        name_item="basic",
        description=f"Basic security group for org {club.id} ({club.name})",
    )
    # Add user
    rbac_add_user_to_group(club.secretary, group)

    # Add roles
    for rule in ORGS_RBAC_GROUPS_AND_ROLES:
        rbac_add_role_to_group(
            group=group,
            app=ORGS_RBAC_GROUPS_AND_ROLES[rule]["app"],
            model=ORGS_RBAC_GROUPS_AND_ROLES[rule]["model"],
            action=ORGS_RBAC_GROUPS_AND_ROLES[rule]["action"],
            rule_type="Allow",
            model_id=club.id,
        )

    # Also add orgs.org as this is the easiest way to check if a user should have access
    rbac_add_role_to_group(
        group=group,
        app="orgs",
        model="org",
        action="view",
        rule_type="Allow",
        model_id=club.id,
    )

    # Add admin - no need to add roles, the tree is enough for user admin
    admin_group = rbac_create_admin_group(
        name_qualifier=club.rbac_admin_name_qualifier,
        name_item="admin",
        description=f"Admin people for {club.id} ({club.name})",
    )
    rbac_add_user_to_admin_group(club.secretary, admin_group)

    # Don't give user tree access to this branch or they can create new groups
    # TODO: Test this
    rbac_admin_add_tree_to_group(admin_group, club.rbac_admin_name_qualifier + ".basic")


@login_required()
def admin_club_rbac_add_basic(request, club_id):
    """Manage RBAC basic set up for a Club

    This doesn't control who gets access - clubs can do that themselves, this controls whether it is basic
    or advanced RBAC configuration. It is the RBAC structure, not the content.

    """

    # Get club
    club = get_object_or_404(Organisation, pk=club_id)

    has_access, role = _rbac_user_has_admin(club, request.user)
    if not has_access:
        return rbac_forbidden(request, role)

    # Check rbac setup
    rbac_basic, rbac_advanced = rbac_get_basic_and_advanced(club)

    # Double check before creating
    if rbac_advanced or rbac_basic:
        messages.error(
            request,
            "This club is already set up with RBAC.",
            extra_tags="cobalt-message-error",
        )
    else:  # create it

        _admin_club_rbac_add_basic_sub(club)

        messages.success(
            request,
            f"{club.name} set up with Basic RBAC",
            extra_tags="cobalt-message-success",
        )

    return redirect("organisations:admin_club_rbac", club_id=club.id)


def _admin_club_rbac_add_advanced_sub(club):
    """low level steps to add rbac advanced for club"""

    # Create groups

    # Create admin group - no need to add roles, the tree is enough for user admin
    admin_group = rbac_create_admin_group(
        name_qualifier=club.rbac_admin_name_qualifier,
        name_item="admin",
        description=f"Admin people for {club.id} ({club.name})",
    )
    rbac_add_user_to_admin_group(club.secretary, admin_group)

    # Add roles - multiple groups with a single role each
    for rule in ORGS_RBAC_GROUPS_AND_ROLES:
        group = rbac_create_group(
            name_qualifier=club.rbac_name_qualifier,
            name_item=rule,
            description=f"{ORGS_RBAC_GROUPS_AND_ROLES[rule]['description']} for {club.id} ({club.name})",
        )
        # Add user
        rbac_add_user_to_group(club.secretary, group)

        rbac_add_role_to_group(
            group=group,
            app=ORGS_RBAC_GROUPS_AND_ROLES[rule]["app"],
            model=ORGS_RBAC_GROUPS_AND_ROLES[rule]["model"],
            action=ORGS_RBAC_GROUPS_AND_ROLES[rule]["action"],
            rule_type="Allow",
            model_id=club.id,
        )

        # Also add orgs.org as this is the easiest way to check if a user should have access
        rbac_add_role_to_group(
            group=group,
            app="orgs",
            model="org",
            action="view",
            rule_type="Allow",
            model_id=club.id,
        )

        # Add admin tree
        rbac_admin_add_tree_to_group(admin_group, club.rbac_name_qualifier + f".{rule}")


@login_required()
def admin_club_rbac_add_advanced(request, club_id):
    """Manage RBAC advanced set up for a Club

    This doesn't control who gets access - clubs can do that themselves, this controls whether it is basic
    or advanced RBAC configuration. It is the RBAC structure, not the content.

    """

    # Get club
    club = get_object_or_404(Organisation, pk=club_id)

    has_access, role = _rbac_user_has_admin(club, request.user)
    if not has_access:
        return rbac_forbidden(request, role)

    # Check rbac setup
    rbac_basic, rbac_advanced = rbac_get_basic_and_advanced(club)

    # Double check before creating
    if rbac_advanced or rbac_basic:
        messages.error(
            request,
            "This club is already set up with RBAC.",
            extra_tags="cobalt-message-error",
        )
    else:  # create it

        _admin_club_rbac_add_advanced_sub(club)

        messages.success(
            request,
            f"{club.name} set up with Advanced RBAC",
            extra_tags="cobalt-message-success",
        )

    return redirect("organisations:admin_club_rbac", club_id=club.id)


@login_required()
def admin_club_rbac_convert_basic_to_advanced(request, club_id):
    """Change rbac setup for a club basic -> advanced"""

    # Get club
    club = get_object_or_404(Organisation, pk=club_id)

    has_access, role = _rbac_user_has_admin(club, request.user)
    if not has_access:
        return rbac_forbidden(request, role)

    status, msg = admin_club_rbac_convert_basic_to_advanced_sub(club)

    if status:
        messages.success(
            request,
            "Club set up with Advanced RBAC. Check permissions, all users will have every access.",
            extra_tags="cobalt-message-success",
        )
    else:
        messages.error(
            request,
            msg,
            extra_tags="cobalt-message-error",
        )

    return redirect("organisations:admin_club_rbac", club_id=club.id)


def admin_club_rbac_convert_basic_to_advanced_sub(club):
    """Change rbac from basic to advanced. Do the actual changes. Does not check for permissions, the calling
    function must handle that.

    Args:
        club: Organisation

    Returns:
        Boolean - success or failure
        Str - error message or None
    """

    # Check rbac setup
    rbac_basic, rbac_advanced = rbac_get_basic_and_advanced(club)

    # Double check before creating
    if rbac_advanced:
        return False, "This club is already set up with advanced RBAC."

    # set up advanced structure
    _admin_club_rbac_add_advanced_sub(club)

    # migrate across - any users get all access
    old_group_name = "rbac.orgs.clubs.generated.%s.%s.basic" % (
        club.state.lower(),
        club.id,
    )
    users = rbac_get_users_in_group_by_name(old_group_name)

    # add all users to all advanced groups. Admin can filter out later. This is the same access they had before
    for user in users:
        for rule in ORGS_RBAC_GROUPS_AND_ROLES:
            group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.{rule}")
            rbac_add_user_to_group(user, group)

    # delete basic
    rbac_delete_group_by_name(old_group_name)

    # Admin groups are the same whether basic or advanced so leave alone

    return True, None


@login_required()
def admin_club_rbac_convert_advanced_to_basic(request, club_id):
    """Change rbac setup for a club advanced -> basic"""

    # Get club
    club = get_object_or_404(Organisation, pk=club_id)

    has_access, role = _rbac_user_has_admin(club, request.user)
    if not has_access:
        return rbac_forbidden(request, role)

    status, msg = admin_club_rbac_convert_advanced_to_basic_sub(club)

    if status:
        messages.success(
            request,
            "Club set up with Basic RBAC.",
            extra_tags="cobalt-message-success",
        )
    else:
        messages.error(
            request,
            msg,
            extra_tags="cobalt-message-error",
        )
    return redirect("organisations:admin_club_rbac", club_id=club.id)


def admin_club_rbac_convert_advanced_to_basic_sub(club):
    """Change rbac from advanced to basic. Do the actual changes. Does not check for permissions, the calling
    function must handle that.

    Args:
        club: Organisation

    Returns:
        Boolean - success or failure
        Str - error message or None
    """

    # Check rbac setup
    rbac_basic, rbac_advanced = rbac_get_basic_and_advanced(club)

    # Double check before creating
    if rbac_basic:
        return False, "This club is already set up with basic RBAC."

    # set up basic structure
    _admin_club_rbac_add_basic_sub(club)

    # migrate access across - any user goes into the one group
    # find the newly created basic group
    new_group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.basic")

    # Go through adding users from old structure to basic group and deleting old groups
    for rule in ORGS_RBAC_GROUPS_AND_ROLES:
        old_group = rbac_get_group_by_name(f"{club.rbac_name_qualifier}.{rule}")
        users = rbac_get_users_in_group(old_group)
        # Add all users to group
        for user in users:
            rbac_add_user_to_group(user, new_group)
        # delete group
        rbac_delete_group(old_group)

    # Admin groups are the same whether basic or advanced so leave alone

    return True, None
