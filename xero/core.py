import logging
from datetime import timedelta, date
from urllib.parse import urlencode

import requests
import base64

from django.utils.timezone import now

from cobalt.settings import (
    XERO_CLIENT_ID,
    XERO_CLIENT_SECRET,
    XERO_TENANT_NAME,
    XERO_BANK_ACCOUNT_CODE,
    COBALT_HOSTNAME,
)
from xero.models import XeroCredentials, XeroInvoice

logger = logging.getLogger("etime")


class XeroApi:
    def __init__(self):

        # load credentials
        credentials, _ = XeroCredentials.objects.get_or_create()
        self.access_token = credentials.access_token
        self.refresh_token = credentials.refresh_token
        self.tenant_id = credentials.tenant_id

        # Build redirect URL from COBALT_HOSTNAME
        protocol = (
            "http"
            if "127.0.0.1" in COBALT_HOSTNAME or "localhost" in COBALT_HOSTNAME
            else "https"
        )
        self.redirect_url = f"{protocol}://{COBALT_HOSTNAME}/xero/callback"

        # Static data
        self.token_refresh_url = "https://identity.xero.com/connect/token"
        self.exchange_code_url = "https://identity.xero.com/connect/token"
        self.connections_url = "https://api.xero.com/connections"
        self.authorisation_url = "https://login.xero.com/identity/connect/authorize"
        self.scope = "offline_access accounting.transactions accounting.contacts payroll.employees payroll.payruns payroll.payslip payroll.timesheets payroll.settings"
        self.b64_id_secret = base64.b64encode(
            bytes(f"{XERO_CLIENT_ID}:{XERO_CLIENT_SECRET}", "utf-8")
        ).decode("utf-8")
        self.xero_auth_url = f"{self.authorisation_url}?response_type=code&client_id={XERO_CLIENT_ID}&redirect_uri={self.redirect_url}&scope={self.scope}&state=123"

    def headers(self):
        """return API headers"""

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Xero-tenant-id": self.tenant_id,
            "Accept": "application/json",
        }

    def refresh_using_authorisation_code(self, authorisation_code):
        """pass Xero an authorisation code and get an access token back"""

        response = requests.post(
            self.exchange_code_url,
            headers={"Authorization": f"Basic {self.b64_id_secret}"},
            data={
                "grant_type": "authorization_code",
                "code": authorisation_code,
                "redirect_uri": self.redirect_url,
            },
        )

        json_response = response.json()

        access_token = json_response["access_token"]
        refresh_token = json_response["refresh_token"]

        credentials, _ = XeroCredentials.objects.get_or_create()
        credentials.authorisation_code = authorisation_code
        credentials.access_token = access_token
        credentials.refresh_token = refresh_token
        credentials.expires = now() + timedelta(seconds=json_response["expires_in"] - 2)
        credentials.save()

        self.access_token = access_token
        self.refresh_token = refresh_token

        logger.info("Updated access token using authorisation code")

    def refresh_xero_tokens(self):
        """the access token expires quickly but can be reset using the refresh token"""

        # See if still valid
        credentials, _ = XeroCredentials.objects.get_or_create()
        if credentials.expires and credentials.expires > now():
            logger.info("Access token is still valid. Not refreshing.")
            return {"message": "Access token is still valid. Not refreshing."}

        logger.info("Refreshing access token")

        # Update access token using refresh token
        response = requests.post(
            self.token_refresh_url,
            headers={
                "Authorization": f"Basic {self.b64_id_secret}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
        )

        json_response = response.json()
        if "access_token" not in json_response:
            return json_response

        credentials.access_token = json_response["access_token"]
        credentials.expires = now() + timedelta(seconds=json_response["expires_in"] - 2)
        credentials.refresh_token = json_response["refresh_token"]
        credentials.save()

        self.access_token = credentials.access_token
        self.refresh_token = credentials.refresh_token

        return json_response

    def set_tenant_id(self):
        """get the tenant id from Xero. We only support one tenant at a time"""

        logger.info("Getting tenants")

        response = requests.get(
            self.connections_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )

        json_response = response.json()

        for tenant in json_response:
            if tenant["tenantName"] == XERO_TENANT_NAME:
                self.tenant_id = tenant["tenantId"]
                credentials, _ = XeroCredentials.objects.get_or_create()
                credentials.tenant_id = self.tenant_id
                credentials.save()
                logger.info(f"Updated tenant id for {XERO_TENANT_NAME}")
                return

        logger.error(f"No tenants found matching {XERO_TENANT_NAME}")

    def xero_api_get(self, url):
        """generic api call for GET"""
        self.refresh_xero_tokens()
        logger.info(url)
        return requests.get(url, headers=self.headers()).json()

    def xero_api_post(self, url, json_data):
        """generic api call for POST"""
        self.refresh_xero_tokens()
        logger.info(url)
        return requests.post(url, headers=self.headers(), json=json_data).json()

    def xero_api_put(self, url, json_data):
        """generic api call for PUT"""
        self.refresh_xero_tokens()
        logger.info(url)
        return requests.put(url, headers=self.headers(), json=json_data).json()

    # -----------------------------------------------------------------------
    # Customer (Contact) methods
    # -----------------------------------------------------------------------

    def create_organisation_contact(self, organisation) -> str | None:
        """Create a Xero contact for an Organisation and save the contact ID back.

        Returns the Xero ContactID on success, or None on failure.
        """
        payload = {
            "Contacts": [
                {
                    "AccountNumber": organisation.org_id,
                    "ContactStatus": "ACTIVE",
                    "Name": organisation.name,
                    "EmailAddress": organisation.club_email or "",
                    "Addresses": [
                        {
                            "AddressType": "STREET",
                            "AddressLine1": organisation.address1 or "",
                            "AddressLine2": organisation.address2 or "",
                            "City": organisation.suburb or "",
                            "Region": organisation.state or "",
                            "PostalCode": organisation.postcode or "",
                            "Country": "Australia",
                        }
                    ],
                }
            ]
        }
        response = self.xero_api_post(
            "https://api.xero.com/api.xro/2.0/Contacts", payload
        )

        contacts = response.get("Contacts", [])
        if not contacts:
            logger.error(
                f"Failed to create Xero contact for {organisation.name}: {response}"
            )
            return None

        contact_id = contacts[0].get("ContactID")
        if not contact_id:
            logger.error(f"No ContactID returned for {organisation.name}: {response}")
            return None

        organisation.xero_contact_id = contact_id
        organisation.save(update_fields=["xero_contact_id"])
        logger.info(
            f"Created Xero contact {contact_id} for organisation {organisation.name}"
        )
        return contact_id

    def update_organisation_contact(self, organisation) -> bool:
        """Update an existing Xero contact with current Organisation data.

        Returns True on success, False on failure.
        """
        if not organisation.xero_contact_id:
            logger.error(
                f"Organisation {organisation.name} has no xero_contact_id — "
                "use create_organisation_contact first"
            )
            return False

        payload = {
            "Contacts": [
                {
                    "ContactID": organisation.xero_contact_id,
                    "AccountNumber": organisation.org_id,
                    "Name": organisation.name,
                    "EmailAddress": organisation.club_email or "",
                    "Addresses": [
                        {
                            "AddressType": "STREET",
                            "AddressLine1": organisation.address1 or "",
                            "AddressLine2": organisation.address2 or "",
                            "City": organisation.suburb or "",
                            "Region": organisation.state or "",
                            "PostalCode": organisation.postcode or "",
                            "Country": "Australia",
                        }
                    ],
                }
            ]
        }
        response = self.xero_api_post(
            "https://api.xero.com/api.xro/2.0/Contacts", payload
        )

        contacts = response.get("Contacts", [])
        if not contacts:
            logger.error(
                f"Failed to update Xero contact for {organisation.name}: {response}"
            )
            return False

        logger.info(
            f"Updated Xero contact {organisation.xero_contact_id} for organisation {organisation.name}"
        )
        return True

    def archive_organisation_contact(self, organisation) -> bool:
        """Archive a Xero contact and clear the stored contact ID on the Organisation.

        Xero does not allow true deletion when a contact has transactions.
        Returns True on success, False on failure.
        """
        if not organisation.xero_contact_id:
            logger.error(f"Organisation {organisation.name} has no xero_contact_id")
            return False

        payload = {
            "Contacts": [
                {
                    "ContactID": organisation.xero_contact_id,
                    "ContactStatus": "ARCHIVED",
                }
            ]
        }
        response = self.xero_api_post(
            "https://api.xero.com/api.xro/2.0/Contacts", payload
        )

        contacts = response.get("Contacts", [])
        if not contacts:
            logger.error(
                f"Failed to archive Xero contact for {organisation.name}: {response}"
            )
            return False

        organisation.xero_contact_id = ""
        organisation.save(update_fields=["xero_contact_id"])
        logger.info(f"Archived Xero contact for organisation {organisation.name}")
        return True

    # -----------------------------------------------------------------------
    # Invoice methods
    # -----------------------------------------------------------------------

    def create_invoice(
        self,
        organisation,
        line_items: list,
        reference: str,
        invoice_type: str = "ACCREC",
        due_days: int = 15,
    ):
        """Create an invoice in Xero and save a local XeroInvoice record.

        Args:
            organisation: The Organisation to invoice.
            line_items: List of dicts with keys: description, quantity, unit_amount,
                        account_code. Optional key: tax_type (defaults to NONE).
            reference: Invoice reference / description string.
            invoice_type: "ACCREC" (accounts receivable) or "ACCPAY" (accounts payable).
            due_days: Days from today until the invoice is due.

        Returns:
            XeroInvoice instance on success, or None on failure.
        """
        if not organisation.xero_contact_id:
            logger.error(
                f"Organisation {organisation.name} has no xero_contact_id — "
                "use create_organisation_contact first"
            )
            return None

        today = date.today()
        due_date = today + timedelta(days=due_days)

        xero_line_items = [
            {
                "Description": item["description"],
                "Quantity": item["quantity"],
                "UnitAmount": float(item["unit_amount"]),
                "AccountCode": item["account_code"],
                "TaxType": item.get("tax_type", "NONE"),
                "LineAmount": float(item["quantity"]) * float(item["unit_amount"]),
            }
            for item in line_items
        ]

        total = sum(
            float(item["quantity"]) * float(item["unit_amount"]) for item in line_items
        )

        payload = {
            "Invoices": [
                {
                    "Type": invoice_type,
                    "Contact": {"ContactID": organisation.xero_contact_id},
                    "LineItems": xero_line_items,
                    "Date": f"{today:%Y-%m-%d}",
                    "DueDate": f"{due_date:%Y-%m-%d}",
                    "Reference": reference,
                    "Status": "AUTHORISED",
                }
            ]
        }

        response = self.xero_api_post(
            "https://api.xero.com/api.xro/2.0/Invoices", payload
        )

        invoices = response.get("Invoices", [])
        if not invoices:
            logger.error(
                f"Failed to create invoice for {organisation.name}: {response}"
            )
            return None

        xero_invoice_data = invoices[0]
        xero_invoice_id = xero_invoice_data.get("InvoiceID")
        if not xero_invoice_id:
            logger.error(f"No InvoiceID returned for {organisation.name}: {response}")
            return None

        xero_invoice = XeroInvoice(
            organisation=organisation,
            xero_invoice_id=xero_invoice_id,
            invoice_number=xero_invoice_data.get("InvoiceNumber", ""),
            invoice_type=invoice_type,
            amount=total,
            status=xero_invoice_data.get("Status", "AUTHORISED"),
            reference=reference,
            date=today,
            due_date=due_date,
        )
        xero_invoice.save()

        logger.info(f"Created Xero invoice {xero_invoice_id} for {organisation.name}")
        return xero_invoice

    def get_invoice(self, xero_invoice_id: str) -> dict:
        """Fetch invoice details from Xero.

        Returns the raw Xero API response dict.
        """
        return self.xero_api_get(
            f"https://api.xero.com/api.xro/2.0/Invoices/{xero_invoice_id}"
        )

    def void_invoice(self, xero_invoice_id: str) -> bool:
        """Void an invoice in Xero and update the local XeroInvoice record.

        Returns True on success, False on failure.
        """
        payload = {"Invoices": [{"InvoiceID": xero_invoice_id, "Status": "VOIDED"}]}
        response = self.xero_api_post(
            f"https://api.xero.com/api.xro/2.0/Invoices/{xero_invoice_id}", payload
        )

        invoices = response.get("Invoices", [])
        if not invoices:
            logger.error(f"Failed to void invoice {xero_invoice_id}: {response}")
            return False

        XeroInvoice.objects.filter(xero_invoice_id=xero_invoice_id).update(
            status="VOIDED"
        )
        logger.info(f"Voided Xero invoice {xero_invoice_id}")
        return True

    # -----------------------------------------------------------------------
    # Payment methods
    # -----------------------------------------------------------------------

    def create_payment(
        self,
        xero_invoice_id: str,
        amount: float,
        payment_date=None,
        account_code: str | None = None,
    ) -> dict:
        """Record a payment against an invoice in Xero.

        Args:
            xero_invoice_id: The Xero invoice UUID.
            amount: Payment amount.
            payment_date: Date of payment (defaults to today).
            account_code: Xero bank account code. Defaults to XERO_BANK_ACCOUNT_CODE
                          from settings.

        Returns:
            The raw Xero API response dict.
        """
        if payment_date is None:
            payment_date = date.today()

        if account_code is None:
            account_code = XERO_BANK_ACCOUNT_CODE

        payload = {
            "Payments": [
                {
                    "Invoice": {"InvoiceID": xero_invoice_id},
                    "Account": {"Code": account_code},
                    "Date": f"{payment_date:%Y-%m-%d}",
                    "Amount": float(amount),
                }
            ]
        }

        response = self.xero_api_post(
            "https://api.xero.com/api.xro/2.0/Payments", payload
        )

        payments = response.get("Payments", [])
        if payments and payments[0].get("Status") == "AUTHORISED":
            XeroInvoice.objects.filter(xero_invoice_id=xero_invoice_id).update(
                status="PAID"
            )
            logger.info(f"Recorded payment of {amount} for invoice {xero_invoice_id}")
        else:
            logger.error(
                f"Payment may have failed for invoice {xero_invoice_id}: {response}"
            )

        return response

    # -----------------------------------------------------------------------
    # Listing methods
    # -----------------------------------------------------------------------

    def get_invoices_for_organisation(
        self,
        organisation,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list:
        """Fetch all invoices from Xero for an Organisation.

        Args:
            organisation: The Organisation to query.
            date_from: Optional lower bound on invoice date (inclusive).
            date_to: Optional upper bound on invoice date (inclusive).

        Returns:
            List of Xero invoice dicts, or empty list on failure.
        """
        if not organisation.xero_contact_id:
            logger.error(f"Organisation {organisation.name} has no xero_contact_id")
            return []

        params = {"ContactIDs": organisation.xero_contact_id}
        if date_from:
            params["DateFrom"] = f"{date_from:%Y-%m-%d}"
        if date_to:
            params["DateTo"] = f"{date_to:%Y-%m-%d}"

        url = f"https://api.xero.com/api.xro/2.0/Invoices?{urlencode(params)}"
        response = self.xero_api_get(url)
        return response.get("Invoices", [])

    def get_payments_for_organisation(
        self,
        organisation,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list:
        """Fetch all payments from Xero for an Organisation.

        Payments are retrieved by fetching paid invoices for the contact and
        extracting the embedded payment details from each invoice.  The optional
        date range filters on invoice date.  Each returned dict is a Xero
        Payment object augmented with ``InvoiceID``, ``InvoiceNumber``, and
        ``InvoiceReference`` from the parent invoice.

        Args:
            organisation: The Organisation to query.
            date_from: Optional lower bound on invoice date (inclusive).
            date_to: Optional upper bound on invoice date (inclusive).

        Returns:
            List of payment dicts, or empty list on failure.
        """
        if not organisation.xero_contact_id:
            logger.error(f"Organisation {organisation.name} has no xero_contact_id")
            return []

        params = {
            "ContactIDs": organisation.xero_contact_id,
            "Statuses": "PAID",
        }
        if date_from:
            params["DateFrom"] = f"{date_from:%Y-%m-%d}"
        if date_to:
            params["DateTo"] = f"{date_to:%Y-%m-%d}"

        url = f"https://api.xero.com/api.xro/2.0/Invoices?{urlencode(params)}"
        response = self.xero_api_get(url)
        invoices = response.get("Invoices", [])

        payments = []
        for invoice in invoices:
            for payment in invoice.get("Payments", []):
                payments.append(
                    {
                        **payment,
                        "InvoiceID": invoice.get("InvoiceID"),
                        "InvoiceNumber": invoice.get("InvoiceNumber"),
                        "InvoiceReference": invoice.get("Reference"),
                    }
                )

        return payments
