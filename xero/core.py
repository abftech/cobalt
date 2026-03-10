import json
import logging
import base64
from datetime import timedelta, date
from urllib.parse import urlencode

import requests

from django.utils.timezone import now

from cobalt.settings import (
    XERO_CLIENT_ID,
    XERO_CLIENT_SECRET,
    XERO_BANK_ACCOUNT_CODE,
    XERO_SETTLEMENT_ACCOUNT_CODE,
)
from xero.models import XeroCredentials, XeroInvoice

logger = logging.getLogger("etime")


class XeroApi:
    def __init__(self):

        # load credentials
        credentials, _ = XeroCredentials.objects.get_or_create()
        self.access_token = credentials.access_token
        self.tenant_id = credentials.tenant_id

        # Static data
        self.token_url = "https://identity.xero.com/connect/token"
        self.b64_id_secret = base64.b64encode(
            bytes(f"{XERO_CLIENT_ID}:{XERO_CLIENT_SECRET}", "utf-8")
        ).decode("utf-8")

    def headers(self):
        """return API headers"""

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Xero-tenant-id": self.tenant_id,
            "Accept": "application/json",
        }

    def refresh_xero_tokens(self):
        """Get an access token via client credentials. Skips if still valid."""

        credentials, _ = XeroCredentials.objects.get_or_create()
        if credentials.expires and credentials.expires > now():
            logger.info("Access token is still valid. Not refreshing.")
            return {"message": "Access token is still valid. Not refreshing."}

        logger.info(f"Fetching new access token from {self.token_url}")

        response = requests.post(
            self.token_url,
            headers={
                "Authorization": f"Basic {self.b64_id_secret}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )

        logger.info(f"Token endpoint responded with HTTP {response.status_code}")

        if not response.text:
            logger.error("Token endpoint returned an empty body")
            return {
                "error": f"Empty response from token endpoint (HTTP {response.status_code})"
            }

        try:
            json_response = response.json()
        except Exception:
            logger.error(
                f"Token endpoint returned non-JSON (HTTP {response.status_code}): {response.text[:200]}"
            )
            return {
                "error": f"Non-JSON from token endpoint (HTTP {response.status_code})",
                "body": response.text[:200],
            }

        if "access_token" not in json_response:
            logger.error(
                f"Failed to get access token (HTTP {response.status_code}): {json_response}"
            )
            return json_response

        credentials.access_token = json_response["access_token"]
        credentials.expires = now() + timedelta(seconds=json_response["expires_in"] - 2)
        credentials.save()

        self.access_token = credentials.access_token
        logger.info("Access token obtained successfully")
        return json_response

    def _save_tenant_id(self, tenant_id: str):
        """Persist tenant_id to the database and update self."""
        self.tenant_id = tenant_id
        credentials, _ = XeroCredentials.objects.get_or_create()
        credentials.tenant_id = tenant_id
        credentials.save()
        logger.info(f"Saved tenant_id: {tenant_id}")

    def _decode_jwt_payload(self) -> dict | None:
        """Decode the JWT access token payload without verifying the signature."""
        if not self.access_token:
            logger.error("No access token available — run Connect first")
            return None
        try:
            parts = self.access_token.split(".")
            if len(parts) != 3:
                logger.error("Access token is not a valid JWT")
                return None
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(payload_b64))
        except Exception as e:
            logger.error(f"Failed to decode JWT access token: {e}")
            return None

    def set_tenant_id(self) -> str | None:
        """Resolve the Xero tenant ID and save it.

        For Custom Connections the token scope is ``app.connections``.  The
        tenant ID is not embedded in the JWT, so we call the connections
        endpoint (which works with this scope and does not require a tenant ID
        header).  We match the connection using the ``authEventId`` field,
        which corresponds to the ``authentication_event_id`` claim in the JWT.

        Returns the tenant ID on success, None on failure.
        """
        # Decode the JWT to get the authentication_event_id for matching
        jwt_payload = self._decode_jwt_payload()
        auth_event_id = (
            jwt_payload.get("authentication_event_id") if jwt_payload else None
        )
        logger.info(f"JWT authentication_event_id: {auth_event_id}")

        # Call the connections endpoint with Xero-User-Id set to the
        # authentication_event_id from the JWT (required for Custom Connections)
        conn_headers = {"Authorization": f"Bearer {self.access_token}"}
        if auth_event_id:
            conn_headers["Xero-User-Id"] = auth_event_id

        response = requests.get(
            "https://api.xero.com/connections", headers=conn_headers
        )

        logger.info(f"Connections endpoint HTTP {response.status_code}")

        if not response.text:
            logger.error(
                f"Empty response from connections endpoint (HTTP {response.status_code})"
            )
            return None

        try:
            connections = response.json()
        except Exception:
            logger.error(f"Non-JSON from connections endpoint: {response.text[:200]}")
            return None

        if not isinstance(connections, list):
            logger.error(f"Unexpected connections response: {connections}")
            return None

        if not connections:
            logger.error(
                "Connections endpoint returned an empty list — check the Custom Connection app is linked to an organisation in the Xero developer portal"
            )
            return None

        logger.info(
            f"Connections: {[(c.get('tenantName'), c.get('tenantId')) for c in connections]}"
        )

        # Match by authEventId (links this token to the right connection)
        if auth_event_id:
            for conn in connections:
                if conn.get("authEventId") == auth_event_id:
                    self._save_tenant_id(conn["tenantId"])
                    return conn["tenantId"]

        # Fall back to using the only available connection
        if len(connections) == 1:
            conn = connections[0]
            logger.warning(f"Using sole available connection: {conn.get('tenantName')}")
            self._save_tenant_id(conn["tenantId"])
            return conn["tenantId"]

        logger.error(f"Could not determine tenant from {len(connections)} connections")
        return None

    def _parse_response(self, response) -> dict:
        """Parse a Xero API response, handling empty or non-JSON bodies."""
        if not response.text:
            hints = {
                401: "Access token is invalid — click 'Connect to Xero' to refresh.",
                403: "Permission denied — check the tenant ID is set and the Custom Connection app has the required scopes (accounting.contacts, accounting.transactions).",
            }
            msg = f"Empty response from Xero (HTTP {response.status_code})"
            if response.status_code in hints:
                msg += f" {hints[response.status_code]}"
            logger.error(msg)
            return {"error": msg}
        try:
            return response.json()
        except Exception:
            logger.error(
                f"Xero API returned non-JSON body (status {response.status_code}): {response.text[:200]}"
            )
            return {
                "error": f"Non-JSON response from Xero (HTTP {response.status_code})",
                "body": response.text[:200],
            }

    def _check_credentials(self) -> dict | None:
        """Return an error dict if tenant_id is not set, otherwise None."""
        if not self.tenant_id:
            msg = "Xero tenant ID is not set. Click 'Connect to Xero' first."
            logger.error(msg)
            return {"error": msg}
        return None

    def xero_api_get(self, url):
        """generic api call for GET"""
        self.refresh_xero_tokens()
        if err := self._check_credentials():
            return err
        logger.info(url)
        return self._parse_response(requests.get(url, headers=self.headers()))

    def xero_api_post(self, url, json_data):
        """generic api call for POST"""
        self.refresh_xero_tokens()
        if err := self._check_credentials():
            return err
        logger.info(url)
        return self._parse_response(
            requests.post(url, headers=self.headers(), json=json_data)
        )

    def xero_api_put(self, url, json_data):
        """generic api call for PUT"""
        self.refresh_xero_tokens()
        if err := self._check_credentials():
            return err
        logger.info(url)
        return self._parse_response(
            requests.put(url, headers=self.headers(), json=json_data)
        )

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

    def create_settlement_invoice(
        self,
        organisation,
        bank_settlement_amount: float,
        reference: str,
    ):
        """Create an ACCPAY invoice in Xero for a settlement payment to a club.

        The invoice is left as AUTHORISED (not paid). Payment confirmation comes
        later via bank feed reconciliation in Xero, detected by the
        sync_xero_invoice_status management command.

        If the organisation has no xero_contact_id, one is created on demand.

        Args:
            organisation: The Organisation being settled.
            bank_settlement_amount: Net amount to be paid out (after ABF fees).
            reference: Human-readable reference string for the invoice.

        Returns:
            XeroInvoice instance on success, None on failure.
        """
        if not organisation.xero_contact_id:
            logger.info(
                f"Organisation {organisation.name} has no xero_contact_id — creating contact"
            )
            contact_id = self.create_organisation_contact(organisation)
            if not contact_id:
                logger.error(
                    f"Failed to create Xero contact for {organisation.name} — cannot create settlement invoice"
                )
                return None

        line_items = [
            {
                "description": reference,
                "quantity": 1,
                "unit_amount": bank_settlement_amount,
                "account_code": XERO_SETTLEMENT_ACCOUNT_CODE,
            }
        ]

        return self.create_invoice(
            organisation=organisation,
            line_items=line_items,
            reference=reference,
            invoice_type="ACCPAY",
            due_days=0,
        )

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
