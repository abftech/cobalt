from django.shortcuts import render

from cobalt.settings import COBALT_HOSTNAME
from organisations.models import Organisation
from xero.core import XeroApi
from xero.models import XeroCredentials

PRODUCTION_HOSTS = ["myabf.com.au", "www.myabf.com.au"]


def connect_htmx(request):
    """Get a client-credentials token and resolve the tenant ID."""

    xero = XeroApi()

    # Force a fresh token regardless of expiry
    credentials, _ = XeroCredentials.objects.get_or_create()
    credentials.expires = None
    credentials.save()

    token_result = xero.refresh_xero_tokens()

    if "access_token" in token_result:
        tenant_id = xero.set_tenant_id()
        result = {
            "token": "ok",
            "tenant_id": tenant_id or "NOT SET — check logs for details",
        }
    else:
        result = {"error": "Token fetch failed", "detail": token_result}

    response = render(request, "xero/json_data.html", {"json_data": result})
    response["HX-Trigger"] = '{"update_config": "true"}'
    return response


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
        if COBALT_HOSTNAME in PRODUCTION_HOSTS:
            result = {"error": "Create Club is not available in production"}
        else:
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

    elif cmd == "create_invoice":
        if COBALT_HOSTNAME in PRODUCTION_HOSTS:
            result = {"error": "Create Invoice is not available in production"}
        else:
            result = {"error": "create_invoice not yet implemented"}

    else:
        result = {"error": f"Unknown command: {cmd!r}"}

    response = render(request, "xero/json_data.html", {"json_data": result})
    response["HX-Trigger"] = '{"update_config": "true"}'
    return response
