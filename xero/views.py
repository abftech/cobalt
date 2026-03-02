from django.shortcuts import render, redirect
from django.urls import reverse

from organisations.models import Organisation
from xero.core import XeroApi
from xero.models import XeroCredentials


def initialise(request):
    """direct a user to grant initial permissions for us from xero"""

    auth_url = XeroApi().xero_auth_url

    return render(request, "xero/initialise.html", {"auth_url": auth_url})


def callback(request):
    """initial callback when a user is sent to Xero to provide access for us"""

    authorisation_code = request.GET.get("code")

    xero = XeroApi()
    xero.refresh_using_authorisation_code(authorisation_code)
    xero.set_tenant_id()

    return redirect(reverse("xero:xero_home"))


def home(request):
    """Main page for Xero"""
    xero = XeroApi()
    return render(request, "xero/home.html", {"xero": xero})


def home_configuration_htmx(request):
    """HTMX table with config data"""

    xero = XeroApi()
    xero_credentials = XeroCredentials.objects.first()
    return render(
        request,
        "xero/home_configuration_htmx.html",
        {"xero": xero, "xero_credentials": xero_credentials},
    )


def refresh_keys_htmx(request):
    """Refresh Xero access tokens"""

    xero = XeroApi()
    json_data = xero.refresh_xero_tokens()

    response = render(request, "xero/json_data.html", {"json_data": json_data})
    response["HX-Trigger"] = '{"update_config": "true"}'
    return response


def run_xero_api_htmx(request):
    """Run a named Xero API command and return the result as JSON"""

    xero = XeroApi()
    cmd = request.POST.get("cmd")
    org_id = request.POST.get("org_id")

    result = {}

    if cmd == "list_contacts":
        result = xero.xero_api_get("https://api.xero.com/api.xro/2.0/Contacts")

    elif cmd == "create_contact":
        organisation = Organisation.objects.filter(id=org_id).first()
        if organisation:
            contact_id = xero.create_organisation_contact(organisation)
            result = {"ContactID": contact_id, "Name": organisation.name}
        else:
            result = {"error": f"Organisation {org_id} not found"}

    elif cmd == "update_contact":
        organisation = Organisation.objects.filter(id=org_id).first()
        if organisation:
            success = xero.update_organisation_contact(organisation)
            result = {"success": success, "Name": organisation.name}
        else:
            result = {"error": f"Organisation {org_id} not found"}

    elif cmd == "archive_contact":
        organisation = Organisation.objects.filter(id=org_id).first()
        if organisation:
            success = xero.archive_organisation_contact(organisation)
            result = {"success": success, "Name": organisation.name}
        else:
            result = {"error": f"Organisation {org_id} not found"}

    response = render(request, "xero/json_data.html", {"json_data": result})
    response["HX-Trigger"] = '{"update_config": "true"}'
    return response
