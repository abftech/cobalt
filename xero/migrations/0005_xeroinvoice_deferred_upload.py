# Generated manually for deferred Xero upload feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("xero", "0004_xerolog"),
    ]

    operations = [
        # Remove the unique constraint on xero_invoice_id and allow blank values
        # (PENDING_UPLOAD records have no xero_invoice_id yet).
        migrations.AlterField(
            model_name="xeroinvoice",
            name="xero_invoice_id",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        # Add new status choices (stored in CharField — no DB constraint change needed,
        # but we update the field definition so Django is in sync).
        migrations.AlterField(
            model_name="xeroinvoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("AUTHORISED", "Authorised"),
                    ("PAID", "Paid"),
                    ("VOIDED", "Voided"),
                    ("PENDING_UPLOAD", "Pending Upload"),
                    ("UPLOADING", "Uploading"),
                    ("UPLOAD_FAILED", "Upload Failed"),
                ],
                default="AUTHORISED",
                max_length=15,
            ),
        ),
        # Cobalt-assigned idempotency key used as the Xero InvoiceNumber.
        migrations.AddField(
            model_name="xeroinvoice",
            name="cobalt_reference",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        # Full Xero API payload stored at settlement time; cleared after upload.
        migrations.AddField(
            model_name="xeroinvoice",
            name="upload_payload",
            field=models.JSONField(blank=True, null=True),
        ),
        # Number of failed upload attempts (UPLOAD_FAILED after 5).
        migrations.AddField(
            model_name="xeroinvoice",
            name="upload_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        # Last error message from a failed upload attempt.
        migrations.AddField(
            model_name="xeroinvoice",
            name="upload_error",
            field=models.TextField(blank=True, default=""),
        ),
    ]
