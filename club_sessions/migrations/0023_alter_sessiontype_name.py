# Generated by Django 3.2.13 on 2022-07-29 20:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0022_remove_sessionmiscpayment_misc_pay_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessiontype",
            name="name",
            field=models.CharField(max_length=20),
        ),
    ]
