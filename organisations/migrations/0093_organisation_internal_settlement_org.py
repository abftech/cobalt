# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0092_alter_memberclubdetails_latest_membership"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="internal_settlement_org",
            field=models.BooleanField(
                default=False,
                help_text="If set, settlement creates Cobalt transactions but no Xero invoices.",
            ),
        ),
    ]
