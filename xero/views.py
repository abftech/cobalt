import base64
import hashlib
import hmac as hmac_lib
import json as json_lib
import logging

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
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
    organisations = Organisation.objects.order_by("name")
    return render(
        request, "xero/home.html", {"xero": xero, "organisations": organisations}
    )


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
                    result = {
                        "InvoiceNumber": invoice.invoice_number,
                        "XeroInvoiceId": invoice.xero_invoice_id,
                        "Organisation": organisation.name,
                        "Amount": str(invoice.amount),
                        "Status": invoice.status,
                        "DueDate": str(invoice.due_date),
                    }
                except ValueError as e:
                    result = {"error": str(e)}
                except TypeError as e:
                    result = {"error": f"Invalid field value: {e}"}

    elif cmd == "create_payment":
        if COBALT_HOSTNAME in PRODUCTION_HOSTS:
            result = {"error": "Create Payment is not available in production"}
        else:
            xero_invoice_id = request.POST.get("xero_invoice_id", "")
            invoice = XeroInvoice.objects.filter(
                xero_invoice_id=xero_invoice_id
            ).first()
            if not invoice:
                result = {"error": f"Invoice {xero_invoice_id!r} not found locally"}
            else:
                try:
                    amount = float(request.POST.get("amount", invoice.amount))
                    payment_date_str = request.POST.get("payment_date", "")
                    account_code = request.POST.get("account_code", "") or None
                    from datetime import date as date_type

                    payment_date = (
                        date_type.fromisoformat(payment_date_str)
                        if payment_date_str
                        else None
                    )
                    response = xero.create_payment(
                        xero_invoice_id=xero_invoice_id,
                        amount=amount,
                        payment_date=payment_date,
                        account_code=account_code,
                    )
                    payments = response.get("Payments", [])
                    if payments and payments[0].get("Status") == "AUTHORISED":
                        result = {
                            "PaymentID": payments[0].get("PaymentID"),
                            "InvoiceNumber": invoice.invoice_number,
                            "Organisation": invoice.organisation.name,
                            "Amount": amount,
                            "Status": "AUTHORISED",
                        }
                    else:
                        result = {
                            "error": "Payment may have failed — check application logs",
                            "detail": response,
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

    _json_str = json_lib.dumps(result)
    _json_str = (
        _json_str.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    response = render(
        request,
        "xero/json_data.html",
        {"json_data": result, "json_data_str": mark_safe(_json_str)},
    )
    response["HX-Trigger"] = '{"update_config": "true"}'
    return response


def payment_form_htmx(request):
    """Return the create-payment form fragment."""
    from cobalt.settings import XERO_BANK_ACCOUNT_CODE

    invoices = (
        XeroInvoice.objects.filter(status="AUTHORISED")
        .select_related("organisation")
        .order_by("organisation__name", "invoice_number")
    )
    return render(
        request,
        "xero/payment_form_htmx.html",
        {"invoices": invoices, "default_account_code": XERO_BANK_ACCOUNT_CODE},
    )


def transactions_htmx(request):
    """Show local Cobalt XeroInvoice records for an organisation."""

    org_id = request.POST.get("org_id")
    organisation = Organisation.objects.filter(id=org_id).first()
    if not organisation:
        return render(
            request,
            "xero/transactions_htmx.html",
            {"error": f"Organisation {org_id!r} not found"},
        )

    invoices = XeroInvoice.objects.filter(organisation=organisation).order_by(
        "-date", "-created_at"
    )
    return render(
        request,
        "xero/transactions_htmx.html",
        {"organisation": organisation, "invoices": invoices},
    )


def reconcile_transactions_htmx(request):
    """Compare local XeroInvoice records against Xero for an organisation."""

    org_id = request.POST.get("org_id")
    organisation = Organisation.objects.filter(id=org_id).first()
    if not organisation:
        return render(
            request,
            "xero/reconcile_transactions_htmx.html",
            {"error": f"Organisation {org_id!r} not found"},
        )

    xero = XeroApi()
    local_invoices = list(
        XeroInvoice.objects.filter(organisation=organisation).order_by("-date")
    )
    xero_invoices = xero.get_invoices_for_organisation(organisation)

    local_by_xero_id = {inv.xero_invoice_id: inv for inv in local_invoices}
    xero_by_id = {
        inv["InvoiceID"]: inv for inv in xero_invoices if inv.get("InvoiceID")
    }

    matched = []
    for local in local_invoices:
        xero_inv = xero_by_id.get(local.xero_invoice_id)
        if xero_inv:
            diffs = []
            if local.status != xero_inv.get("Status", ""):
                diffs.append(
                    {
                        "field": "Status",
                        "local": local.status,
                        "xero": xero_inv.get("Status", ""),
                    }
                )
            try:
                if abs(float(local.amount) - float(xero_inv.get("Total", 0))) > 0.01:
                    diffs.append(
                        {
                            "field": "Amount",
                            "local": str(local.amount),
                            "xero": str(xero_inv.get("Total", "")),
                        }
                    )
            except (TypeError, ValueError):
                pass
            matched.append({"local": local, "xero": xero_inv, "diffs": diffs})

    local_only = [
        inv for inv in local_invoices if inv.xero_invoice_id not in xero_by_id
    ]
    xero_only = [
        inv for inv in xero_invoices if inv.get("InvoiceID") not in local_by_xero_id
    ]
    differences_count = sum(1 for m in matched if m["diffs"])

    return render(
        request,
        "xero/reconcile_transactions_htmx.html",
        {
            "organisation": organisation,
            "matched": matched,
            "local_only": local_only,
            "xero_only": xero_only,
            "differences_count": differences_count,
        },
    )


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


def reconcile_contacts_htmx(request):
    """Compare active Xero contacts against Cobalt organisations and report discrepancies."""
    xero = XeroApi()

    data = xero.xero_api_get(
        "https://api.xero.com/api.xro/2.0/Contacts"
        "?where=ContactStatus%3D%3D%22ACTIVE%22"
    )
    if "error" in data:
        return render(request, "xero/reconcile_contacts_htmx.html", {"error": data})

    xero_contacts = data.get("Contacts", [])
    xero_by_id = {c["ContactID"]: c for c in xero_contacts if c.get("ContactID")}

    # All Xero ContactIDs currently stored in Cobalt
    linked_ids = set(
        Organisation.objects.exclude(xero_contact_id="")
        .exclude(xero_contact_id__isnull=True)
        .values_list("xero_contact_id", flat=True)
    )

    missing_from_xero = []
    stale_ids = []
    data_mismatches = []
    matched_count = 0

    for org in Organisation.objects.order_by("name"):
        if not org.xero_contact_id:
            missing_from_xero.append(org)
        elif org.xero_contact_id not in xero_by_id:
            stale_ids.append(org)
        else:
            matched_count += 1
            xero_c = xero_by_id[org.xero_contact_id]
            diffs = []
            if org.name != xero_c.get("Name", ""):
                diffs.append(
                    {
                        "field": "Name",
                        "cobalt": org.name,
                        "xero": xero_c.get("Name", ""),
                    }
                )
            cobalt_email = org.club_email or ""
            xero_email = xero_c.get("EmailAddress", "")
            if cobalt_email != xero_email:
                diffs.append(
                    {"field": "Email", "cobalt": cobalt_email, "xero": xero_email}
                )
            if diffs:
                data_mismatches.append({"org": org, "diffs": diffs})

    orphans_in_xero = [
        c
        for c in xero_contacts
        if c.get("ContactID") and c["ContactID"] not in linked_ids
    ]

    return render(
        request,
        "xero/reconcile_contacts_htmx.html",
        {
            "matched_count": matched_count,
            "missing_from_xero": missing_from_xero,
            "stale_ids": stale_ids,
            "data_mismatches": data_mismatches,
            "orphans_in_xero": orphans_in_xero,
            "total_xero": len(xero_contacts),
            "total_cobalt": Organisation.objects.count(),
        },
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
    logger.info(f"Xero webhook received: {len(request.body)} bytes")

    signature = request.META.get("HTTP_X_XERO_SIGNATURE", "")
    computed = base64.b64encode(
        hmac_lib.new(
            XERO_WEBHOOK_KEY.encode(),
            request.body,
            hashlib.sha256,
        ).digest()
    ).decode()

    if not hmac_lib.compare_digest(signature, computed):
        logger.warning(
            "Xero webhook: invalid signature — check XERO_WEBHOOK_KEY matches the Xero developer portal"
        )
        return HttpResponse(status=401)

    payload = json_lib.loads(request.body)
    events = payload.get("events", [])
    logger.info(f"Xero webhook: {len(events)} event(s)")

    for event in events:
        category = event.get("eventCategory")
        event_type = event.get("eventType")
        resource_id = event.get("resourceId")
        logger.info(
            f"Xero webhook event: {category}/{event_type} resourceId={resource_id}"
        )
        if category == "INVOICE":
            _handle_invoice_webhook(resource_id)
        else:
            logger.info(f"Xero webhook: ignoring event category {category!r}")

    return HttpResponse(status=200)
