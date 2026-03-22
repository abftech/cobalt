:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

========================================
Setting Up the Xero Integration
========================================

This guide walks through everything required to connect Cobalt to Xero — from
creating the Xero app in the developer portal to verifying the connection. It
covers both the **test/demo** and **production** environments.

Cobalt uses Xero's **Custom Connection** (machine-to-machine OAuth 2.0 client
credentials). There is no user-facing consent screen or callback URL. Cobalt
exchanges its client credentials directly for an access token whenever it needs
to make API calls.

For the developer API reference (XeroApi methods, models, testing patterns) see
:doc:`using_xero`.

----

Prerequisites
-------------

* A Cobalt environment is already running (test server or production).
* You have a Xero account with **admin access** to the target organisation.
* You know the Elastic Beanstalk (or local) environment variable configuration
  mechanism for your environment.

----

Xero Account Requirements
--------------------------

Before setting up the integration, the Xero organisation (and your Xero account)
must meet the following requirements.

Subscription plan
~~~~~~~~~~~~~~~~~

Cobalt uses the Xero Accounting API (contacts, invoices, payments endpoints).
This is available on all standard Xero paid plans. Custom Connection apps —
which Cobalt uses for authentication — are available to any Xero account holder
through the developer portal at no extra cost.

.. note::
   Xero's plan names and feature inclusions change over time. Verify that the
   target organisation's plan includes API access on
   `Xero's pricing page <https://www.xero.com/au/pricing-plans/>`_ before
   proceeding.

For testing, every Xero account includes a **Xero demo company** at no charge.
All development and UAT work should be done against the demo company.

Developer portal access
~~~~~~~~~~~~~~~~~~~~~~~

Creating a Custom Connection app requires access to the
`Xero Developer Portal <https://developer.xero.com/app/manage>`_. Any Xero
account holder can log in to the developer portal and create apps for free —
no separate developer subscription is needed.

Chart of accounts
~~~~~~~~~~~~~~~~~

Cobalt creates invoices and records payments against specific GL account codes.
Those accounts must exist in the Xero chart of accounts before Cobalt can use
them. Two account codes are configured via environment variables:

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 30

   * - Purpose
     - Cobalt setting
     - Required Xero account type
     - Notes
   * - Payment clearing account
     - ``XERO_BANK_ACCOUNT_CODE``
     - **Bank**
     - Used when ``create_payment()`` records that a club has paid an invoice.
       Must be a Bank-type account so it appears under **Banking** in Xero and
       can receive bank feed transactions for reconciliation.
   * - Settlement payables account
     - ``XERO_SETTLEMENT_ACCOUNT_CODE``
     - **Current Liability**
     - Used on the ACCPAY settlement bill (no GST) and the informational ``$0``
       lines on the ACCREC fee invoice. Must accept ``BASEXCLUDED`` / ``NOTAX``
       tax types. **Do not** use a revenue account here.
   * - Fee income account
     - ``XERO_FEE_ACCOUNT_CODE``
     - **Revenue** or **Other Income**
     - Used on the fee-recovery line of the ACCREC fee invoice (with GST).
       Must be a revenue-type account so that Xero accepts ``OUTPUT`` (GST on
       Income) as the tax type. Liability accounts cannot accept ``OUTPUT`` and
       will cause invoice creation to fail.

Additionally, ``create_invoice()`` accepts arbitrary account codes per line item.
These are passed by the calling code and not stored in environment variables —
create the appropriate Revenue or Other Income accounts in Xero for each income
category (affiliation fees, table fees, etc.).

Tax types
~~~~~~~~~

Cobalt sends ``LineAmountTypes: "Inclusive"`` on all invoices, meaning every
``UnitAmount`` passed to Xero already **includes** any applicable GST. Cobalt
uses two distinct tax types for the automatically-created settlement invoices:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Cobalt setting
     - Default value
     - Where used
   * - ``XERO_SETTLEMENT_TAX_TYPE``
     - ``NOTAX``
     - Line items on the **ACCPAY settlement invoice** (the bill paid to the
       club) and the informational ``$0`` lines on the ACCREC fee invoice.
       The ABF is not charging GST on the disbursement — it is passing through
       money that was always the club's. Set to ``BASEXCLUDED`` in the Xero
       chart of accounts (BAS Excluded).
   * - ``XERO_FEE_TAX_TYPE``
     - ``OUTPUT``
     - The fee-recovery line item on the **ACCREC fee invoice** (the invoice
       billed to the club for the ABF's processing fee). The ABF charges GST
       on this service fee. ``OUTPUT`` means 10% GST on income (standard
       Australian rate).

Both values are Xero tax type codes. Valid codes for Australian organisations
include ``OUTPUT`` (GST on income), ``INPUT`` (GST on expenses),
``BASEXCLUDED`` (BAS excluded), and ``NOTAX`` (no tax / exempt). Check
**Accounting → Tax Rates** in Xero for the exact codes available in your
organisation.

The ``create_invoice()`` method (used for manually-created invoices) also
accepts an optional ``tax_type`` per line item; if omitted, no ``TaxType``
is sent and Xero uses the account's default tax setting.

----

Step 1 — Create a Xero Custom Connection App
---------------------------------------------

A separate Xero app (Custom Connection) is required for each Cobalt environment
because each environment connects to a different Xero organisation (demo company
for non-production, production org for production).

1. Log in to the `Xero Developer Portal <https://developer.xero.com/app/manage>`_.
2. Make sure you are connected to the Demo Company (AU)
3. Click **New app**.
4. Fill in the form:

   .. list-table::
      :header-rows: 1
      :widths: 30 70

      * - Field
        - Value
      * - App name
        - ``Cobalt`` (or any descriptive name)
      * - Integration type
        - **Custom Connection**
      * - Company or application URL
        - ``https://www.myabf.com.au`` (or your hostname)

5. Click **Create app**.

.. note::
   Custom Connection apps do not use redirect URIs. There is no OAuth consent
   screen — authentication is handled entirely server-side using client
   credentials.

Configuring the Custom Connection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After creating the app you must configure which Xero organisation it connects
to and what API scopes it requires:

1. In the app settings, go to the **Configuration** tab.
2. Under **Connected organisation**, select the Xero organisation this app
   should access (demo company for test/UAT, production org for production).
3. Under **Scopes**, enable at minimum:

   * ``accounting.contacts``
   * ``accounting.transactions``
   * ``accounting.settings.read``

4. Save the configuration.
5. Copy the **Client ID** and **Client Secret** — you will need them in Step 2.

.. warning::
   Because a Custom Connection app is bound to a single Xero organisation, you
   need a separate app for each environment that connects to a different Xero
   organisation. All environments that share the same demo company can share one
   app.

----

Step 2 — Set Environment Variables
------------------------------------

Set the following variables in the environment configuration for each Cobalt
environment (Elastic Beanstalk environment properties, local ``.env`` file, or
shell exports):

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Variable
     - Description
   * - ``XERO_CLIENT_ID``
     - Client ID from the Xero developer portal
   * - ``XERO_CLIENT_SECRET``
     - Client secret from the Xero developer portal
   * - ``XERO_BANK_ACCOUNT_CODE``
     - Xero account code for the bank/clearing account used when recording
       payments (e.g. ``090``). Look this up in **Chart of Accounts** in Xero.
   * - ``XERO_SETTLEMENT_ACCOUNT_CODE``
     - Xero account code for the settlement payables account (Current Liability).
       Used on the ACCPAY bill and the informational lines of the ACCREC invoice.
   * - ``XERO_FEE_ACCOUNT_CODE``
     - Xero account code for the fee income account (Revenue / Other Income).
       Used on the fee-recovery line of the ACCREC invoice. Must be a revenue
       account so that ``OUTPUT`` tax type is accepted.
   * - ``XERO_SETTLEMENT_TAX_TYPE``
     - Xero tax type code for the settlement disbursement lines (no GST).
       Default: ``NOTAX``. The ABF typically sets this to ``BASEXCLUDED``.
   * - ``XERO_FEE_TAX_TYPE``
     - Xero tax type code for the processing-fee recovery line on ACCREC
       invoices. Default: ``OUTPUT`` (10% GST on income — the ABF charges GST
       on its service fee).

Test vs production values
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use a **Xero demo company** for all non-production environments. Because the
Custom Connection app is bound to a single organisation in the Xero developer
portal, using a demo company simply means creating a separate Custom Connection
app that is linked to the demo company (see Step 1).

.. warning::
   Never configure a non-production Custom Connection app to connect to the
   production Xero organisation. Test code will create real invoices and
   contacts in the live account.

Finding account codes
~~~~~~~~~~~~~~~~~~~~~

In Xero: **Accounting → Chart of Accounts**. The code for each account is shown
in the **Code** column. Common codes used by the ABF:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Variable
     - Example code
     - Typical account name
   * - ``XERO_BANK_ACCOUNT_CODE``
     - ``090``
     - Business bank account or clearing account
   * - ``XERO_SETTLEMENT_ACCOUNT_CODE``
     - ``800``
     - Club settlement payable / accounts payable clearing

The exact codes depend on the chart of accounts for your Xero organisation.

----

Step 3 — Connect Cobalt to Xero
---------------------------------

With the Custom Connection there is no user-facing OAuth consent screen. Cobalt
fetches an access token directly using its client credentials. You trigger this
once from the admin UI to populate the tenant ID and verify the credentials work.

1. Start (or deploy) the Cobalt application with the environment variables from
   Step 2 in place.

2. Log in to Cobalt as an **ABF staff** user (the ``/xero/`` views are
   restricted to staff).

3. Navigate to ``/xero/``.

4. Click **Connect**. Cobalt will:

   a. POST to ``https://identity.xero.com/connect/token`` with the client
      credentials to obtain a fresh access token.
   b. Decode the JWT access token to extract the ``authentication_event_id``.
   c. Call ``GET https://api.xero.com/connections`` (with ``Xero-User-Id`` set
      to the ``authentication_event_id``) to retrieve the linked tenant.
   d. Save the access token, its expiry time, and the tenant UUID to the
      ``XeroCredentials`` database table.

5. Verify that the **Configuration** panel shows:

   * A non-empty tenant ID
   * A non-empty access token
   * An expiry time roughly 30 minutes in the future

If any of these are missing, check the application logs for errors from
``xero.core`` and click **Connect** again.

Token lifecycle
~~~~~~~~~~~~~~~

Access tokens expire after ~30 minutes. Cobalt fetches a new one automatically
before every API call via ``refresh_xero_tokens()`` — no manual intervention is
required. Because client credentials are used, there is no refresh token; a
brand-new access token is obtained directly whenever the current one has expired.

As long as ``XERO_CLIENT_ID`` and ``XERO_CLIENT_SECRET`` remain valid,
the integration will keep working indefinitely without any re-authorisation step.

----

Step 4 — Verify the Connection
---------------------------------

Use the **API playground** on the Xero admin home page (``/xero/``) to confirm
everything is working:

1. Select **List contacts** from the command dropdown and click **Run**.
2. The response panel should show a list of contacts from the connected Xero
   organisation. If the demo company is new it may be empty — that is fine.

If you receive an error, check:

* The environment variables were loaded correctly (restart the app server after
  changing them).
* The Custom Connection app in the Xero developer portal is configured for the
  correct Xero organisation and has the required scopes enabled.

----

Step 5 — Set Up GL Account Codes in Xero
------------------------------------------

Before invoices can be created, the Xero chart of accounts must contain the
account codes referenced in ``XERO_BANK_ACCOUNT_CODE`` and
``XERO_SETTLEMENT_ACCOUNT_CODE``, and any line-item account codes passed to
``create_invoice()``. Each account must be the **correct Xero account type** —
using the wrong type will cause API errors.

In the demo company, Xero pre-populates a standard chart of accounts. You may
need to add or modify accounts to match the codes used in production.

To add or edit an account: **Accounting → Chart of Accounts → Add Account**
(or click an existing account to edit it).

Payment clearing account (XERO_BANK_ACCOUNT_CODE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This account is referenced by ``create_payment()`` when recording that an
invoice has been paid.

* **Xero account type**: ``Bank``
* **Enable payments**: must be enabled (Xero does this automatically for Bank
  accounts)
* **Tax**: not applicable to Bank accounts
* Bank-type accounts appear under the **Banking** menu in Xero and can be
  linked to a bank feed for reconciliation. The ABF typically maps this to the
  actual business transaction account (e.g. code ``090``).

.. note::
   Only **Bank**-type accounts can be used as the payment account in Xero's
   Payments API. Attempting to record a payment against a non-Bank account will
   return an error.

Settlement payables account (XERO_SETTLEMENT_ACCOUNT_CODE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Used on the ACCPAY settlement invoice (the bill paid to the club) and on the
informational ``$0`` lines of the ACCREC fee invoice.

* **Xero account type**: ``Current Liability`` (or ``Accounts Payable``)
* **Tax type**: ``BASEXCLUDED`` / ``NOTAX`` — no GST applies. The ABF is
  disbursing money that was always the club's; it is not the ABF's income.
* When the ABF transfers money to a club and reconciles the bank transaction in
  Xero, the ACCPAY invoice is marked paid and this liability is cleared.

Fee income account (XERO_FEE_ACCOUNT_CODE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Used on the fee-recovery line item of the ACCREC fee invoice (the charge billed
to the club for the ABF's processing fee).

* **Xero account type**: ``Revenue`` or ``Other Income``
* **Tax type**: ``OUTPUT`` (10% GST on income) — the ABF charges GST on its
  processing fee because it is taxable income for the ABF.
* This **must** be a revenue-type account. Current Liability accounts (such as
  ``XERO_SETTLEMENT_ACCOUNT_CODE``) cannot accept ``OUTPUT`` tax type in Xero,
  which would cause invoice creation to fail with the error
  *"The TaxType code 'OUTPUT' cannot be used with account code 'NNN'."*

Revenue / income accounts (``create_invoice()`` line items)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generic ``create_invoice()`` method (used for manually-created invoices such
as affiliation fees) references revenue account codes passed by the calling code.
These codes are **not** stored in Cobalt's environment variables.

* **Xero account type**: ``Revenue`` or ``Other Income``
* **Tax**: Cobalt now sends ``LineAmountTypes: "Inclusive"`` on all invoices.
  If a line item does not include an explicit ``tax_type``, Xero uses the
  account's default tax setting. Set the account default to match what is
  expected (e.g. ``OUTPUT`` for taxable income, ``BASEXCLUDED`` for non-taxable).
* The **Create Invoice** tool in the Xero admin screen (``/xero/``) includes
  a Tax Type dropdown so the correct rate can be selected per line item.
* Create a separate account for each income category, e.g.:

  * Affiliation fees
  * Table fees
  * Entry fees

Ensure the account code strings match exactly what is passed by the Cobalt code
that calls ``create_invoice()`` — they are case-sensitive in Xero.

Verifying account setup
~~~~~~~~~~~~~~~~~~~~~~~

Confirm the accounts are configured correctly by creating a test invoice and
payment via the Django shell::

    from xero.core import XeroApi
    from organisations.models import Organisation

    xero = XeroApi()
    org = Organisation.objects.get(pk=<id>)  # must have xero_contact_id set

    # Test ACCREC invoice with a revenue account code
    invoice = xero.create_invoice(
        organisation=org,
        line_items=[{"description": "Test", "quantity": 1, "unit_amount": 1.00, "account_code": "200"}],
        reference="TEST",
    )
    print(invoice)

    # Test recording a payment (uses XERO_BANK_ACCOUNT_CODE)
    if invoice:
        xero.create_payment(invoice.xero_invoice_id, amount=1.00)
        print("Payment recorded")

----

Onboarding an Organisation
--------------------------

Before invoices can be raised for a club or organisation, a corresponding Xero
**Contact** must exist and its UUID must be saved in
``Organisation.xero_contact_id``.

Via the admin UI
~~~~~~~~~~~~~~~~

1. Go to ``/xero/`` → **API playground**.
2. Select **Create contact**, enter the organisation ID, and click **Run**.
3. On success the ``Organisation.xero_contact_id`` field is populated
   automatically.

Via code (e.g. Django shell)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    from xero.core import XeroApi
    from organisations.models import Organisation

    xero = XeroApi()
    org = Organisation.objects.get(pk=<id>)
    contact_id = xero.create_organisation_contact(org)
    print(f"Contact ID: {contact_id}")

----

Step 6 — Configure Xero Webhooks
---------------------------------

Xero can push real-time notifications to Cobalt whenever an invoice is created
or updated. This is the primary mechanism Cobalt uses to keep ``XeroInvoice``
status fields in sync — webhooks eliminate the need to poll Xero for every
outstanding invoice.

Setting up the webhook in the Xero developer portal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Log in to the `Xero Developer Portal <https://developer.xero.com/app/manage>`_
   and open your Custom Connection app.
2. Go to the **Webhooks** tab.
3. Click **Add Webhook** and fill in:

   .. list-table::
      :header-rows: 1
      :widths: 30 70

      * - Field
        - Value
      * - Webhook URL
        - ``https://<your-hostname>/xero/webhook``
          (e.g. ``https://www.myabf.com.au/xero/webhook``)
      * - Event types
        - Select **Invoices** (covers both CREATE and UPDATE events)

4. Click **Save**. Xero will immediately send an **Intent to Receive**
   validation request — a POST with an empty ``events`` list and a valid
   HMAC-SHA256 signature. Cobalt verifies the signature and returns HTTP 200,
   completing the handshake automatically.
5. Copy the **Webhook key** shown on the Webhooks tab. This is the signing
   secret used to verify every incoming request.

Setting ``XERO_WEBHOOK_KEY``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the webhook signing key as an environment variable:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Variable
     - Description
   * - ``XERO_WEBHOOK_KEY``
     - The webhook signing key from the Xero developer portal Webhooks tab.

How the webhook endpoint works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every request Xero sends carries an ``x-xero-signature`` header containing a
Base64-encoded HMAC-SHA256 signature of the raw request body, signed with the
webhook key. Cobalt:

1. Recomputes the HMAC-SHA256 using ``XERO_WEBHOOK_KEY``.
2. Compares it to the header using a constant-time comparison. If they do not
   match, returns HTTP 401 (and logs a warning).
3. For each event with ``eventCategory == "INVOICE"``, fetches the current
   invoice status from Xero and updates the local ``XeroInvoice`` record if
   the status has changed.
4. Returns HTTP 200.

The endpoint is exempt from CSRF checks (it is machine-to-machine) and is
allowed through maintenance mode so Xero can always reach it.

.. note::
   The Intent to Receive handshake sends a payload with ``"events": []``.
   Cobalt handles this correctly — it verifies the signature and returns 200
   without attempting to process any events.

Cron Job — Invoice Status Sync (fallback)
------------------------------------------

Cobalt also includes a management command that polls Xero for outstanding
invoice statuses. Now that webhooks provide real-time updates, this command
serves as a **daily fallback** to catch any events that may have been missed
(e.g. during downtime):

::

    python manage.py sync_xero_invoice_status

Schedule this as a daily cron job on the EC2 instances. Running it hourly is
no longer necessary once webhooks are configured. The command is safe to run
on all environments; it only reads from Xero and updates the local
``XeroInvoice.status`` field.

----

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Symptom
     - Fix
   * - ``401 Unauthorized`` on API calls
     - The client credentials are invalid or the Custom Connection app has been
       disabled/revoked in the Xero developer portal. Check ``XERO_CLIENT_ID``
       and ``XERO_CLIENT_SECRET``, then click **Connect** again.
   * - Token fetch returns an error instead of ``access_token``
     - The client credentials are wrong, or the app's scopes have not been saved
       correctly in the Xero developer portal. Re-check the app configuration.
   * - Account code not found error on invoice creation
     - The account code passed to ``create_invoice()`` does not exist in the
       connected Xero organisation. Add it in **Accounting → Chart of Accounts**.
   * - Fee invoice shows ``AUTHORISED`` but not ``PAID`` in Xero
     - The auto-payment step after uploading the fee invoice failed. Check the
       ``BatchStatus`` summary for ``upload_xero_settlements`` in Django admin
       (``/admin/utils/batchstatus/``) — the exact Xero error is recorded there.
       Common causes: ``XERO_BANK_ACCOUNT_CODE`` not set or set to an invalid
       code; Xero rejected the payment amount.
   * - GST not appearing on the fee recovery invoice
     - ``XERO_FEE_TAX_TYPE`` is not set to ``OUTPUT``. Check the environment
       variable and ensure the ``XERO_SETTLEMENT_ACCOUNT_CODE`` account in Xero
       does not restrict the tax type to BAS Excluded only.
   * - Token refresh succeeds but tenant ID is blank
     - ``set_tenant_id()`` could not retrieve a connection. Check the application
       logs and confirm the Custom Connection app is linked to an organisation in
       the Xero developer portal.

----

Summary of Environment Variables
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Variable
     - Required
     - Notes
   * - ``XERO_CLIENT_ID``
     - Yes
     - From Xero developer portal. Each environment that connects to a different
       Xero organisation needs its own Custom Connection app and client ID.
   * - ``XERO_CLIENT_SECRET``
     - Yes
     - From Xero developer portal.
   * - ``XERO_BANK_ACCOUNT_CODE``
     - Yes
     - GL account code for the bank/clearing account used when recording
       payments. Must be a Bank-type account in Xero.
   * - ``XERO_SETTLEMENT_ACCOUNT_CODE``
     - Yes
     - GL account code for the settlement payables account (Current Liability).
       Used on ACCPAY bills and the informational lines of ACCREC fee invoices.
   * - ``XERO_FEE_ACCOUNT_CODE``
     - Yes
     - GL account code for the fee income account (Revenue / Other Income).
       Used on the fee-recovery line of the ACCREC invoice. Must accept
       ``OUTPUT`` tax type — use a revenue account, not a liability account.
   * - ``XERO_SETTLEMENT_TAX_TYPE``
     - No
     - Xero tax type for settlement disbursement lines. Default: ``NOTAX``.
       Set to ``BASEXCLUDED`` for Australian BAS-excluded disbursements.
   * - ``XERO_FEE_TAX_TYPE``
     - No
     - Xero tax type for the fee-recovery line on ACCREC invoices.
       Default: ``OUTPUT`` (10% GST on income).
   * - ``XERO_WEBHOOK_KEY``
     - Yes (if webhooks are configured)
     - Signing key from the Xero developer portal Webhooks tab. Required to
       verify the HMAC-SHA256 signature on incoming webhook requests.

Resetting the Demo Company
--------------------------

The demo company will reset back to the defaults after about 28 days.
If you want to reset it now, you can login and visit: https://my.xero.com/!xkcD/Dashboard
At the bottom in very small print is the link to reset it.

Resetting the Demo Company breaks the Custom Connection so this needs to be deleted and rebuilt.

After rebuilding it, you will probably want to create the clubs in Xero. To do this, ssh to
the test server and run::

    ./manage.py shell_plus

    >>> Organisation.objects.update(xero_contact_id="")

Exit shell_plus and run::

    ./manage.py create_missing_xero_contacts

