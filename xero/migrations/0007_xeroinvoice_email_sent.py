# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("xero", "0006_xeroinvoice_auto_record_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="xeroinvoice",
            name="email_sent",
            field=models.BooleanField(default=False),
        ),
    ]
