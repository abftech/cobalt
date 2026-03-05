import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0080_alter_membertransaction_club_session_id_and_more"),
        ("xero", "0002_xeroinvoice"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisationtransaction",
            name="xero_invoice",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="organisation_transactions",
                to="xero.xeroinvoice",
            ),
        ),
    ]
