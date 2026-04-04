:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

==================================
Adding Stripe to Cobalt
==================================

Pre-requisites
==============

First, set up your basic Cobalt environment (see :doc:`../tutorials/getting_started`).

Stripe Setup
===============

Create an account with Stripe, you will need to use a unique email address, but Stripe
allow you to have as many test accounts as you like. You can then create an API key
through Stripe's web site.

Go to https://dashboard.stripe.com/test/apikeys

Then add a webhook to Stripe:

https://dashboard.stripe.com/webhooks

We need two events to be sent:

* payment_method.attached
* charge.succeeded

The webhook location is:

https://<your environment>.myabf.com.au/payments/stripe-webhook

After creating the webhook endpoint, reveal the **Signing secret** on the webhook detail
page (Stripe Dashboard → Developers → Webhooks → select your endpoint → Signing secret).
You will need this value for ``STRIPE_WEBHOOK_SECRET`` below.

Environment Variables
=====================

You need to set the following environment variables to the values obtained in the previous steps:

* ``STRIPE_SECRET_KEY`` — secret API key
* ``STRIPE_PUBLISHABLE_KEY`` — publishable API key
* ``STRIPE_WEBHOOK_SECRET`` — webhook signing secret (``whsec_...``). Enables signature
  verification on incoming webhook calls. If not set, signature verification is skipped
  (legacy mode — not recommended for production).

Running
=======

To run this in a hosted environment, you need to set up the web callback address within Stripe.

To run this in development, you need to install the Stripe CLI and run::

    stripe login
    stripe listen --forward-to 127.0.0.1:8000/payments/stripe-webhook

The ``stripe listen`` command prints a webhook signing secret (``whsec_...``) to the terminal.
Set this as ``STRIPE_WEBHOOK_SECRET`` in your local environment to enable signature verification
during development.