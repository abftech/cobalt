# Generated by Django 3.2.15 on 2023-04-08 08:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0062_organisation_send_results_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="xero_contact_id",
            field=models.CharField(default="", max_length=50, null=True),
        ),
    ]
