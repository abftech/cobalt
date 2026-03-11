import base64
import hashlib
import hmac as hmac_lib
import json as json_lib
import logging

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cobalt.settings import COBALT_HOSTNAME, XERO_WEBHOOK_KEY
from organisations.models import Organisation
from xero.core import XeroApi
from xero.models import XeroCredentials, XeroInvoice

logger = logging.getLogger("cobalt")

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
            organisation = Organisation.objects.filter(id=org_id).first()
            if not organisation:
                result = {"error": f"Organisation {org_id} not found"}
            elif not organisation.xero_contact_id:
                result = {
                    "error": f"{organisation.name} has no Xero contact ID — create the contact first"
                }
            else:
                try:
                    line_items = [
                        {
                            "description": request.POST.get("description", ""),
                            "quantity": float(request.POST.get("quantity", 1)),
                            "unit_amount": float(request.POST.get("unit_amount", 0)),
                            "account_code": request.POST.get("account_code", ""),
                        }
                    ]
                    invoice = xero.create_invoice(
                        organisation=organisation,
                        line_items=line_items,
                        reference=request.POST.get("reference", ""),
                        invoice_type=request.POST.get("invoice_type", "ACCREC"),
                        due_days=int(request.POST.get("due_days", 15)),
                    )
                    if invoice:
                        result = {
                            "InvoiceNumber": invoice.invoice_number,
                            "XeroInvoiceId": invoice.xero_invoice_id,
                            "Organisation": organisation.name,
                            "Amount": str(invoice.amount),
                            "Status": invoice.status,
                            "DueDate": str(invoice.due_date),
                        }
                    else:
                        result = {
                            "error": "Invoice creation failed — check application logs"
                        }
                except (ValueError, TypeError) as e:
                    result = {"error": f"Invalid field value: {e}"}

    elif cmd == "archive_all_contacts":
        if COBALT_HOSTNAME in PRODUCTION_HOSTS:
            result = {"error": "Archive All Contacts is not available in production"}
        else:
            data = xero.xero_api_get(
                "https://api.xero.com/api.xro/2.0/Contacts"
                "?where=ContactStatus%3D%3D%22ACTIVE%22"
            )
            contacts = data.get("Contacts", [])
            archived = 0
            failed = 0
            for contact in contacts:
                contact_id = contact.get("ContactID")
                if not contact_id:
                    continue
                archive_result = xero.xero_api_post(
                    "https://api.xero.com/api.xro/2.0/Contacts",
                    {
                        "Contacts": [
                            {"ContactID": contact_id, "ContactStatus": "ARCHIVED"}
                        ]
                    },
                )
                if archive_result.get("Contacts"):
                    archived += 1
                    Organisation.objects.filter(xero_contact_id=contact_id).update(
                        xero_contact_id=""
                    )
                else:
                    failed += 1
            result = {"archived": archived, "failed": failed, "total": len(contacts)}

    elif cmd == "create_all_contacts":
        if COBALT_HOSTNAME in PRODUCTION_HOSTS:
            result = {
                "error": "Create All Missing Clubs is not available in production"
            }
        else:
            orgs = Organisation.objects.filter(
                Q(xero_contact_id__isnull=True) | Q(xero_contact_id="")
            ).order_by("name")
            total = orgs.count()
            created = 0
            failed = 0
            for org in orgs:
                contact_id = xero.create_organisation_contact(org)
                if contact_id:
                    created += 1
                else:
                    failed += 1
            result = {"created": created, "failed": failed, "total": total}

    else:
        result = {"error": f"Unknown command: {cmd!r}"}

    response = render(request, "xero/json_data.html", {"json_data": result})
    response["HX-Trigger"] = '{"update_config": "true"}'
    return response


def invoice_form_htmx(request):
    """Return the create-invoice form fragment."""
    organisations = (
        Organisation.objects.exclude(xero_contact_id__isnull=True)
        .exclude(xero_contact_id="")
        .order_by("name")
    )
    return render(
        request,
        "xero/invoice_form_htmx.html",
        {"organisations": organisations},
    )


def _handle_invoice_webhook(xero_invoice_id: str):
    """Fetch current invoice status from Xero and update the local XeroInvoice."""
    local = XeroInvoice.objects.filter(xero_invoice_id=xero_invoice_id).first()
    if not local:
        return
    xero = XeroApi()
    data = xero.get_invoice(xero_invoice_id)
    invoices = data.get("Invoices", [])
    if invoices:
        new_status = invoices[0].get("Status")
        if new_status and new_status != local.status:
            old_status = local.status
            local.status = new_status
            local.save(update_fields=["status", "updated_at"])
            logger.info(
                f"Xero webhook: invoice {local.invoice_number} {old_status} -> {new_status}"
            )


@require_POST
@csrf_exempt
def xero_webhook(request):
    """Receive and process Xero webhook event notifications.

    Xero signs every request with HMAC-SHA256 using the webhook key configured
    in the Xero developer portal.  We verify the signature before processing.

    For the Intent to Receive handshake (0 events) we simply verify the
    signature and return 200 — no further action needed.
    """
    signature = request.META.get("HTTP_X_XERO_SIGNATURE", "")
    computed = base64.b64encode(
        hmac_lib.new(
            XERO_WEBHOOK_KEY.encode(),
            request.body,
            hashlib.sha256,
        ).digest()
    ).decode()

    if not hmac_lib.compare_digest(signature, computed):
        logger.warning("Xero webhook: invalid signature")
        return HttpResponse(status=401)

    payload = json_lib.loads(request.body)
    for event in payload.get("events", []):
        if event.get("eventCategory") == "INVOICE":
            _handle_invoice_webhook(event["resourceId"])

    return HttpResponse(status=200)
