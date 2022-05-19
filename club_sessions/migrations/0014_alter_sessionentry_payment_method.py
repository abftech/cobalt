# Generated by Django 3.2.12 on 2022-05-19 05:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0064_auto_20211009_1824"),
        ("club_sessions", "0013_alter_sessionentry_player"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessionentry",
            name="payment_method",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="payments.orgpaymentmethod",
            ),
        ),
    ]
