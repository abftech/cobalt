:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

========================================
Using Xero
========================================

Example::

    from xero.core import XeroApi

    xero = XeroApi()
    org = Organisation.objects.get(org_id="1234")

      # Create contact
      xero.create_organisation_contact(org)

      # Issue a receivable invoice
      invoice = xero.create_invoice(
          organisation=org,
          line_items=[{"description": "ABF Settlement June", "quantity": 1, "unit_amount": 344.55, "account_code": "200"}],
          reference="ABF-JUNE-2026",
          invoice_type="ACCREC",
          due_days=30,
      )

      # Record payment
      xero.create_payment(invoice.xero_invoice_id, amount=344.55)