# Generated by Django 3.2.10 on 2022-07-20 02:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0055_organisation_default_secondary_payment_type"),
    ]

    operations = [
        migrations.RenameField(
            model_name="organisation",
            old_name="default_secondary_payment_type",
            new_name="default_secondary_payment_method",
        ),
    ]
