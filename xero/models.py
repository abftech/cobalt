from django.db import models


class XeroLog(models.Model):
    """Record of every API call made to the Xero API"""

    STATUS_SUCCESS = "Success"
    STATUS_FAILURE = "Failure"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILURE, "Failure"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=10)
    url = models.CharField(max_length=500)
    request_body = models.TextField(blank=True)
    response_body = models.TextField(blank=True)
    http_status_code = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.method} {self.url} — {self.status} ({self.created_at:%Y-%m-%d %H:%M})"


class XeroInvoice(models.Model):
    """Local record of an invoice issued through Xero"""

    INVOICE_TYPE_CHOICES = [
        ("ACCREC", "Accounts Receivable"),
        ("ACCPAY", "Accounts Payable"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AUTHORISED", "Authorised"),
        ("PAID", "Paid"),
        ("VOIDED", "Voided"),
    ]

    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.PROTECT,
        related_name="xero_invoices",
    )
    xero_invoice_id = models.CharField(max_length=100, unique=True)
    invoice_number = models.CharField(max_length=50, blank=True, default="")
    invoice_type = models.CharField(
        max_length=10, choices=INVOICE_TYPE_CHOICES, default="ACCREC"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="AUTHORISED"
    )
    reference = models.CharField(max_length=255, blank=True, default="")
    online_invoice_url = models.URLField(blank=True, default="")
    date = models.DateField()
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.invoice_number} - {self.organisation.name} - {self.amount}"


class XeroCredentials(models.Model):
    """persistent store for Xero credentials"""

    # The authorisation code is given to use by the user who provides authorisation. We get this from a callback
    authorisation_code = models.CharField(max_length=100, blank=True, default="")

    # The access token is enormous and expires quickly
    access_token = models.CharField(max_length=2000, blank=True, default="")

    # We store the expiry to see if it is still valid for quick succession calls
    expires = models.DateTimeField(null=True)

    # The refresh token is used to get a new (not expired) access_token
    refresh_token = models.CharField(max_length=100, blank=True, default="")

    # The tenant id identifies the company we are using
    tenant_id = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return "Xero Credentials"
