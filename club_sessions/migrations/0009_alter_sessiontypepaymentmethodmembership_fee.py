# Generated by Django 3.2.5 on 2021-10-14 11:26

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0008_alter_sessiontype_master_session_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessiontypepaymentmethodmembership",
            name="fee",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("5"), max_digits=10
            ),
        ),
    ]
