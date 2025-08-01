import requests
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

from accounts.models import User
from cobalt.settings import GLOBAL_MPSERVER, GLOBAL_TITLE
from rbac.core import rbac_user_has_role
from utils.views.general import masterpoint_query
from organisations.forms import OrgForm
from organisations.models import Organisation
from organisations.views.general import (
    get_rbac_model_for_state,
    get_club_data_from_masterpoints_centre,
)


@login_required()
def org_search_ajax(request):
    """Ajax org search function. Used by the generic org search.

    Args:
        orgname - partial org name to search for.

    Returns:
        HttpResponse - either a message or a list of users in HTML format.
    """

    msg = ""

    if request.method == "GET":

        if "orgname" not in request.GET:
            return HttpResponse("orgname missing from request")

        search_org_name = request.GET.get("orgname")
        orgs = Organisation.objects.filter(name__icontains=search_org_name)

        # is_ajax has been removed from Django
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            if orgs.count() > 30:
                msg = "Too many results (%s)" % orgs.count()
                orgs = None
            elif orgs.count() == 0:
                msg = "No matches found"
            html = render_to_string(
                template_name="organisations/org_search_ajax.html",
                context={"orgs": orgs, "msg": msg},
            )

            data_dict = {"data": html}

            return JsonResponse(data=data_dict, safe=False)

    return HttpResponse("invalid request")


@login_required()
def org_detail_ajax(request):
    """Returns basic info on an org for the generic org search.

    Ajax call to get basic info on an org. Will return an empty json array
    if the org number is invalid.

    Args:
        org_id - org number

    Returns:
        Json array: address etc.
    """

    if request.method == "GET" and "org_id" in request.GET:
        org_id = request.GET.get("org_id")
        org = get_object_or_404(Organisation, pk=org_id)
        # is_ajax has been removed from Django
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                template_name="organisations/org_detail_ajax.html",
                context={"org": org},
            )
            data_dict = {"data": html, "org": org.name}
            return JsonResponse(data=data_dict, safe=False)
    return JsonResponse(data={"error": "Invalid request"})


@login_required()
def get_club_details_htmx(request):
    """Get details about club from Masterpoints centre
    This request is called by HTMX and returns HTML, not json"""

    if request.method != "POST" or "club_number" not in request.POST:
        return

    # get club number from form
    club_number = request.POST.get("club_number")

    # initialise return data
    errors = None
    data = {}
    secretary_name = "Not Set"
    secretary_id = None
    club_secs = None
    possible_club_sec_name = "Not Found"

    # check if already exists
    if Organisation.objects.filter(org_id=club_number).exists():
        errors = f"Club already exists in {GLOBAL_TITLE}"
    else:

        # Try loading data from MPC
        data = get_club_data_from_masterpoints_centre(club_number)

        if data:

            # We get a name for club secretary. See if we can find a match
            possible_club_sec_name = data["club_secretary"]

            # ClubSec can be spaces or empty
            if possible_club_sec_name and len(possible_club_sec_name) > 0:
                first_name = possible_club_sec_name.split(" ")[0]
                last_name = possible_club_sec_name.split(" ")[-1]
                club_secs = User.objects.filter(first_name=first_name).filter(
                    last_name=last_name
                )
                if club_secs:  # use the first match
                    secretary_name = club_secs[0]
                    secretary_id = club_secs[0].id

                # Finally we can check security - need to have access for this state

            state = data["state"]
            rbac_model_for_state = get_rbac_model_for_state(state)

            print(state)
            print(rbac_model_for_state)

            if not (
                rbac_user_has_role(
                    request.user, "orgs.state.%s.edit" % rbac_model_for_state
                )
                or rbac_user_has_role(request.user, "orgs.admin.edit")
            ):
                errors = f"You don't have access to add a club to this state ({state})"

        else:
            errors = "Club not found"

    form = OrgForm(initial=data)

    return render(
        request,
        "organisations/admin_add_club_htmx.html",
        {
            "form": form,
            "club_number": club_number,
            "errors": errors,
            "club_secs": club_secs,
            "possible_club_sec_name": possible_club_sec_name,
            "secretary_name": secretary_name,
            "secretary_id": secretary_id,
        },
    )


@login_required()
def club_name_search_htmx(request):
    """Get list of matching club names from Masterpoints centre"""

    if request.method != "POST" or "club_name_search" not in request.POST:
        return HttpResponse("Error")

    # Get partial club name to search for from form
    club_name_search = request.POST.get("club_name_search")

    # Try to load data from MP Server
    qry = f"{GLOBAL_MPSERVER}/clubNameSearch/{club_name_search}"
    club_list = masterpoint_query(qry)

    # We get 11 rows but only show 10 so we know if there is more data or not
    more_data = False
    if len(club_list) > 10:
        more_data = True
        club_list = club_list[:10]

    return render(
        request,
        "organisations/admin_club_search_htmx.html",
        {"club_list": club_list, "more_data": more_data},
    )
