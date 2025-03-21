# Generated by Django 3.2.19 on 2024-08-20 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0077_alter_membermembershiptype_start_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membershiptype",
            name="grace_period_days",
            field=models.IntegerField(
                default=31, verbose_name="Payment period (days from start of period)"
            ),
        ),
    ]
