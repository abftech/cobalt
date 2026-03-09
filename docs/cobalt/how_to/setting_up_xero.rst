:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

========================================
Setting Up the Xero Integration
========================================

This guide walks through everything required to connect Cobalt to Xero — from
creating the Xero app in the developer portal to completing the OAuth handshake
and verifying the connection. It covers both the **test/demo** and
**production** environments.

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

Step 1 — Create a Xero App
---------------------------

The same Xero app can service multiple Cobalt environments by registering
multiple redirect URIs. You only need to create one app in the Xero developer
portal.

1. Log in to the `Xero Developer Portal <https://developer.xero.com/app/manage>`_.
2. Click **New app**.
3. Fill in the form:

   .. list-table::
      :header-rows: 1
      :widths: 30 70

      * - Field
        - Value
      * - App name
        - ``Cobalt`` (or any descriptive name)
      * - Integration type
        - **Web app**
      * - Company or application URL
        - ``https://www.myabf.com.au`` (or your hostname)
      * - Redirect URIs
        - Add one line for **each** environment you need (see below)

4. Click **Create app**.

Redirect URIs to register
~~~~~~~~~~~~~~~~~~~~~~~~~~

Cobalt derives its redirect URI from ``COBALT_HOSTNAME``. Add a line for every
environment:

.. code-block:: text

    http://127.0.0.1:8000/xero/callback        # local development
    https://test.myabf.com.au/xero/callback    # test
    https://uat.myabf.com.au/xero/callback     # UAT
    https://www.myabf.com.au/xero/callback     # production

.. note::
   Xero requires ``https://`` for all non-localhost URIs. The development URI
   using ``http://127.0.0.1:8000`` is treated as a special case by Xero and is
   permitted without TLS.

5. After saving, go to the **Configuration** tab and copy the **Client ID** and
   **Client Secret** — you will need them in Step 2.

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
     - Client ID from the Xero developer portal (same value for all environments)
   * - ``XERO_CLIENT_SECRET``
     - Client secret from the Xero developer portal (same value for all environments)
   * - ``XERO_TENANT_NAME``
     - The **exact display name** of the Xero organisation to connect to.
       This must match what appears in the top-left of the Xero UI.
   * - ``XERO_BANK_ACCOUNT_CODE``
     - Xero account code for the bank/clearing account used when recording
       payments (e.g. ``090``). Look this up in **Chart of Accounts** in Xero.
   * - ``XERO_SETTLEMENT_ACCOUNT_CODE``
     - Xero account code for the club settlement payables account.

Test vs production values
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use a **Xero demo company** for all non-production environments. When you
created your Xero account, Xero automatically provisioned a demo company called
something like ``Demo Company (AU)``. You can also create additional demo
companies from the Xero dashboard.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Environment
     - ``XERO_TENANT_NAME``
     - Notes
   * - Development / Test / UAT
     - ``Demo Company (AU)``
     - Or whatever your demo company is named. Check in Xero → organisation
       switcher (top-left).
   * - Production
     - ``17 Ways``
     - The ABF's live Xero organisation. **Never point test environments here.**

.. warning::
   Setting ``XERO_TENANT_NAME`` to the production organisation on a test server
   will cause test code to create real invoices and contacts in the live Xero
   account. Always double-check this variable before running the OAuth flow.

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

Step 3 — Complete the OAuth Flow
----------------------------------

The OAuth flow links Cobalt to Xero and stores a refresh token in the database.
This step is performed **once per environment** (or any time the tokens are
revoked).

1. Start (or deploy) the Cobalt application with the environment variables from
   Step 2 in place.

2. Log in to Cobalt as an **ABF staff** user (the ``/xero/`` views are
   restricted to staff).

3. Navigate to ``/xero/initialise``.

4. Click **Connect to Xero**. You will be redirected to Xero's authorisation
   screen.

5. Select the correct Xero organisation (demo company for test, production org
   for production) and click **Allow access**.

6. Xero redirects back to ``/xero/callback``. Cobalt will:

   a. Exchange the authorisation code for an access token and refresh token.
   b. Look up all organisations connected to the app and find the one whose
      display name matches ``XERO_TENANT_NAME``.
   c. Save the tenant UUID and tokens to the ``XeroCredentials`` database table.

7. You are redirected to the Xero admin home page (``/xero/``). Verify that
   the **Configuration** panel shows:

   * A non-empty tenant ID
   * A non-empty access token
   * An expiry time roughly 30 minutes in the future

If any of these are missing, check the application logs for errors from
``xero.core`` and re-run the flow.

Token lifecycle
~~~~~~~~~~~~~~~

The access token expires after ~30 minutes. Cobalt refreshes it automatically
before every API call — no manual intervention is required. The refresh token
itself does not expire as long as it is used at least once every 60 days.

If the refresh token is ever revoked (e.g. you disconnect the app from Xero's
**Connected apps** list), you must repeat this step to re-authorise.

----

Step 4 — Verify the Connection
---------------------------------

Use the **API playground** on the Xero admin home page (``/xero/``) to confirm
everything is working:

1. Select **List contacts** from the command dropdown and click **Run**.
2. The response panel should show a list of contacts from the connected Xero
   organisation. If the demo company is new it may be empty — that is fine.

If you receive an error, check:

* The ``XERO_TENANT_NAME`` value matches the organisation name exactly
  (including capitalisation and any trailing spaces).
* The environment variables were loaded correctly (restart the app server after
  changing them).
* The Xero app has not been disconnected from **Xero → My Xero → Connected apps**.

----

Step 5 — Set Up GL Account Codes in Xero
------------------------------------------

Before invoices can be created, the Xero chart of accounts must contain the
account codes referenced in ``XERO_BANK_ACCOUNT_CODE`` and
``XERO_SETTLEMENT_ACCOUNT_CODE``, and any line-item account codes passed to
``create_invoice()``.

In the demo company, Xero pre-populates a standard chart of accounts. You may
need to add or modify accounts to match the codes used in production.

1. In Xero: **Accounting → Chart of Accounts → Add Account**.
2. Set the **Code**, **Name**, **Type** (e.g. *Revenue*, *Current Liability*),
   and **Tax** settings to match the production organisation.
3. Confirm the code is reachable by creating a test invoice via the Cobalt
   admin or the Django shell::

       from xero.core import XeroApi
       from organisations.models import Organisation

       xero = XeroApi()
       org = Organisation.objects.get(pk=<id>)  # must have xero_contact_id set

       invoice = xero.create_invoice(
           organisation=org,
           line_items=[{"description": "Test", "quantity": 1, "unit_amount": 1.00, "account_code": "200"}],
           reference="TEST",
       )
       print(invoice)

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

Cron Job — Invoice Status Sync
--------------------------------

Cobalt runs a management command to sync the status of outstanding invoices
from Xero (to detect payments made directly in Xero, e.g. after bank
reconciliation):

::

    python manage.py sync_xero_invoice_status

This should be scheduled as a cron job on the EC2 instances. A typical schedule
is once per hour. The command is safe to run on all environments; it only reads
from Xero and updates the local ``XeroInvoice.status`` field.

----

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Symptom
     - Fix
   * - ``No tenants found matching <name>``
     - ``XERO_TENANT_NAME`` does not match the organisation name in Xero.
       Check the exact spelling — including capitalisation and spaces — against
       the organisation switcher in the top-left of the Xero UI.
   * - ``401 Unauthorized`` on API calls
     - The access token has been revoked or the refresh token has expired (not
       used in >60 days). Re-run Step 3.
   * - Callback returns ``invalid_grant``
     - The authorisation code was already used (codes are one-time-use). Click
       **Connect to Xero** again to start a fresh flow.
   * - Account code not found error on invoice creation
     - The account code passed to ``create_invoice()`` does not exist in the
       connected Xero organisation. Add it in **Accounting → Chart of Accounts**.
   * - Token refresh succeeds but tenant ID is blank
     - ``set_tenant_id()`` could not match ``XERO_TENANT_NAME``. Check the value
       and confirm the app is authorised for the correct Xero organisation.

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
     - From Xero developer portal. Same across all environments.
   * - ``XERO_CLIENT_SECRET``
     - Yes
     - From Xero developer portal. Same across all environments.
   * - ``XERO_TENANT_NAME``
     - Yes
     - Must exactly match the Xero organisation display name.
       Use demo company for non-production.
   * - ``XERO_BANK_ACCOUNT_CODE``
     - Yes
     - GL account code for recording payments.
   * - ``XERO_SETTLEMENT_ACCOUNT_CODE``
     - Yes
     - GL account code for club settlement payables.
