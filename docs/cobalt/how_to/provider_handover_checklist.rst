:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

==========================================
Provider Handover Checklist
==========================================

This checklist covers every external service and credential that must be
transferred or re-provisioned when handing Cobalt over to a new support
provider. Work through each section in order — AWS must be done first
because most other services depend on it.

.. warning::
   Do **not** revoke old credentials until the new provider has verified
   that the replacement credentials are working in all environments
   (production, UAT, and test). Revoking too early will cause outages.

----

1. AWS Account
==============

Cobalt runs entirely on AWS: the application server (Elastic Beanstalk),
database (RDS), email (SES), notifications (SNS), file storage (EFS/S3),
DNS (Route 53), and load balancer.

Steps
-----

1. Create an IAM user (or transfer ownership of the root account) for the
   new provider in the ABF AWS account.
2. Attach the existing IAM policies used for Cobalt deployments (check the
   existing IAM user to see which policies are attached).
3. Generate a new **Access Key ID** and **Secret Access Key** for the new
   IAM user.
4. Update the following Elastic Beanstalk environment properties in **every
   environment** (Production, UAT, Test) via the AWS Console → Elastic
   Beanstalk → Configuration → Software:

   * ``AWS_ACCESS_KEY_ID``
   * ``AWS_SECRET_ACCESS_KEY``
   * ``AWS_REGION_NAME``

5. Update the AWS CLI and EB CLI credentials on the new provider's local
   machines.
6. Verify access by running ``eb status`` from the ``cobalt`` directory.
7. Revoke the old IAM user's access key once verified.

Key resources
-------------

- Elastic Beanstalk application: ``cobalt`` (region: ``ap-southeast-2``)
- RDS instance: check AWS Console → RDS
- Route 53 hosted zone: ``myabf.com.au``
- SES configuration sets: ``cobalt-prod``, ``cobalt-uat``, ``cobalt-test``

----

2. AWS RDS (Database)
=====================

The PostgreSQL database runs on AWS RDS. The new provider needs the
connection credentials to manage the database directly (migrations, backups,
support queries).

Steps
-----

1. In the AWS Console → RDS → Databases, select the Cobalt instance.
2. Modify the master user password to a new value (requires a maintenance
   window or an immediate apply).
3. Update the following Elastic Beanstalk environment properties in every
   environment:

   * ``RDS_DB_NAME``
   * ``RDS_USERNAME``
   * ``RDS_PASSWORD``
   * ``RDS_HOSTNAME``
   * ``RDS_PORT``

4. Restart the Elastic Beanstalk environment to pick up the new credentials.
5. Verify the application connects successfully by checking the Cobalt home
   page and the Django admin.

----

3. AWS SES (Email)
==================

All transactional email is sent through AWS Simple Email Service. The
verified sending domain (``myabf.com.au``) and configuration sets must
remain active.

Steps
-----

1. Confirm the new AWS IAM user (from step 1) has ``ses:SendEmail`` and
   ``ses:SendRawEmail`` permissions.
2. Verify the ``myabf.com.au`` domain is still verified in SES (AWS Console
   → SES → Verified identities). If domain ownership is transferring, the
   new provider will need to add the SES DKIM DNS records to Route 53.
3. Check each environment's configuration set (AWS Console → SES →
   Configuration sets) and confirm the SNS topic subscription for event
   webhooks is active and pointing to the correct Cobalt URL:
   ``https://<env>.myabf.com.au/notifications/ses/event-webhook/``
4. Update ``AWS_SES_CONFIGURATION_SET``, ``AWS_SES_REGION_NAME``, and
   ``AWS_SES_REGION_ENDPOINT`` in the Elastic Beanstalk environment
   properties if they have changed.
5. Send a test email from the application and confirm the SES webhook
   callback is received (visible in the Django admin under Notifications).

----

4. Stripe (Payments)
====================

Stripe processes all Bridge Credits top-ups and event entry payments.

Steps
-----

1. The ABF Stripe account owner must add the new provider as an
   **Administrator** in the Stripe Dashboard → Settings → Team.
2. If new API keys are needed, go to Stripe Dashboard → Developers → API
   keys → Create restricted key (or roll the existing secret key).
3. Update the following Elastic Beanstalk environment properties in every
   environment:

   * ``STRIPE_SECRET_KEY``
   * ``STRIPE_PUBLISHABLE_KEY``

4. For each environment's webhook endpoint (Stripe Dashboard → Developers
   → Webhooks), verify the endpoint URL is correct:
   ``https://<env>.myabf.com.au/payments/stripe-webhook``
   The endpoint must handle ``payment_method.attached`` and
   ``charge.succeeded`` events.
5. Reveal the **Signing secret** for each webhook endpoint and update
   ``STRIPE_WEBHOOK_SECRET`` in the corresponding environment.
6. Test a payment in the UAT environment using a Stripe test card.

----

5. Xero (Accounting)
====================

The Xero integration raises invoices and records payments for club
settlements. See :doc:`setting_up_xero` for the full setup guide.

Steps
-----

1. The ABF Xero account admin must invite the new provider to the Xero
   organisation (Xero → Settings → Users → Invite a User).
2. In the `Xero Developer Portal <https://developer.xero.com/app/manage>`_,
   transfer ownership of the Cobalt Custom Connection app to the new
   provider's Xero account, or create a new app and update credentials.
3. Update the following Elastic Beanstalk environment properties in
   production (and create equivalent apps for UAT/test):

   * ``XERO_CLIENT_ID``
   * ``XERO_CLIENT_SECRET``

4. Navigate to ``/xero/`` in Cobalt as an ABF staff user and click
   **Connect** to verify the new credentials work.
5. Update the Xero webhook signing key:
   Xero Developer Portal → app → Webhooks → copy the webhook key →
   set ``XERO_WEBHOOK_KEY`` in the environment properties.
6. Confirm the webhook URL is registered:
   ``https://www.myabf.com.au/xero/webhook``

----

6. Google Firebase Cloud Messaging (FCM)
=========================================

FCM delivers push notifications to the Cobalt mobile app (Android and iOS).

Steps
-----

1. In the `Firebase Console <https://console.firebase.google.com>`_, go to
   Project Settings → Users and Permissions and add the new provider as an
   **Owner**.
2. Generate a new service account key: Project Settings → Service Accounts
   → Generate new private key. This downloads a JSON credentials file.
3. Upload the JSON file to a secure location on the Elastic Beanstalk EC2
   instance (or store it in AWS Secrets Manager and update the retrieval
   method).
4. Update the ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable in
   every Elastic Beanstalk environment to point to the new file path.
5. Restart the application and send a test push notification from the
   Django admin to verify FCM is working.
6. Remove the old provider's Firebase access once verified.

----

7. Google reCAPTCHA
====================

reCAPTCHA v2 protects the logged-out contact form from spam submissions.

Steps
-----

1. Go to the `Google reCAPTCHA Admin Console <https://www.google.com/recaptcha/admin>`_
   and transfer ownership of the Cobalt site to the new provider's Google
   account, or create a new reCAPTCHA v2 site for ``myabf.com.au``.
2. Copy the new **Site key** and **Secret key**.
3. Update the following Elastic Beanstalk environment properties in every
   environment:

   * ``RECAPTCHA_SITE_KEY``
   * ``RECAPTCHA_SECRET_KEY``

4. Visit the public contact form and submit a test message to confirm
   reCAPTCHA loads and validates correctly.

----

8. Google Maps
==============

An embedded Google Maps iframe shows venue locations on congress pages.
The Maps API key is currently hardcoded in the event templates.

Steps
-----

1. In the `Google Cloud Console <https://console.cloud.google.com>`_, locate
   the project that owns the Maps Embed API key (search for the existing
   key value in APIs & Services → Credentials).
2. Add the new provider as an **Owner** of the Google Cloud project, or
   create a new Maps Embed API key restricted to ``*.myabf.com.au``.
3. If issuing a new key, update all three template files that embed the
   Maps iframe:

   * ``events/templates/events/players/congress.html``
   * ``events/templates/events/players/congress_logged_out.html``
   * ``events/templates/events/congress_builder/congress_wizard_3.html``

   Replace the ``key=`` parameter in the Maps embed URL in each file.
4. Deploy the updated templates and verify that a congress venue map
   displays correctly.

.. note::
   Ideally the Maps API key should be moved to an environment variable to
   avoid needing a code change when rotating it.

----

9. New Relic (Monitoring)
=========================

New Relic provides application performance monitoring and alerting.

Steps
-----

1. Log in to New Relic and go to Administration → User Management. Add the
   new provider as an **Admin** and remove the old provider once verified.
2. Confirm the ``NEW_RELIC_APP_ID`` values for each environment are set
   correctly in the Elastic Beanstalk environment properties.
3. Verify that the New Relic agent is reporting data for each environment
   (New Relic → APM → cobalt-* applications should all show green).
4. Review and transfer ownership of any alert policies and notification
   channels to the new provider's contact details.

----

10. Domain and DNS (Route 53)
==============================

The ``myabf.com.au`` domain and its DNS records are managed in AWS Route 53.
If the domain is registered elsewhere (e.g. a registrar separate from AWS),
that registrar account must also be transferred.

Steps
-----

1. Confirm who holds the domain registrar account for ``myabf.com.au`` and
   transfer access (or the registration itself) to the new provider.
2. In AWS Route 53 → Hosted zones → ``myabf.com.au``, verify the new
   provider's IAM user (from step 1) has access to manage DNS records.
3. Document all existing DNS records before making any changes.
4. If the domain registrar is separate from AWS, ensure the nameservers
   in the registrar still point to the Route 53 hosted zone.

----

11. Mobile Application (Google Play & Apple App Store)
=======================================================

The Cobalt mobile app is published on both stores under the ABF's accounts.

Steps
-----

1. **Google Play**: Go to the Google Play Console → Users and permissions
   and add the new provider with **Admin** access. Remove the old provider.
2. **Apple App Store**: In App Store Connect → Users and Access, invite the
   new provider as an **Admin**. Remove the old provider once accepted.
3. Transfer any signing certificates and provisioning profiles stored
   outside of the stores (e.g. on a developer machine). The iOS distribution
   certificate and Android keystore must not be lost.
4. Confirm the new provider can successfully build and submit a test build
   to both stores using the transferred credentials.

----

Post-Handover Verification Checklist
=====================================

After completing all sections above, verify end-to-end functionality in
the UAT environment before declaring the handover complete:

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Test
     - Service verified
   * - Log in to Cobalt and view the dashboard
     - AWS EB, RDS
   * - Submit the logged-out contact form (with reCAPTCHA)
     - Google reCAPTCHA, AWS SES
   * - Top up Bridge Credits with a Stripe test card
     - Stripe, AWS SES
   * - Create a congress with a venue address and confirm map displays
     - Google Maps
   * - Send a push notification to a test device via Django admin
     - Firebase FCM
   * - Check New Relic shows live APM data for the UAT environment
     - New Relic
   * - Confirm a Xero invoice can be created from ``/xero/``
     - Xero
   * - Confirm email delivery and SES webhook callback appears in admin
     - AWS SES, SNS
