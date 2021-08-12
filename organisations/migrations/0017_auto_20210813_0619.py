# Generated by Django 3.2.4 on 2021-08-12 20:19

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0016_clublog"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="organisation",
            name="membership_part_year_date",
        ),
        migrations.RemoveField(
            model_name="organisation",
            name="membership_renewal_date",
        ),
        migrations.AddField(
            model_name="organisation",
            name="membership_part_year_date_day",
            field=models.IntegerField(
                blank=True,
                default=1,
                null=True,
                validators=[
                    django.core.validators.MaxValueValidator(31),
                    django.core.validators.MinValueValidator(1),
                ],
                verbose_name="Membership Part Year Date - Day",
            ),
        ),
        migrations.AddField(
            model_name="organisation",
            name="membership_part_year_date_month",
            field=models.IntegerField(
                blank=True,
                default=1,
                null=True,
                validators=[
                    django.core.validators.MaxValueValidator(12),
                    django.core.validators.MinValueValidator(1),
                ],
                verbose_name="Membership Part Year Date - Month",
            ),
        ),
        migrations.AddField(
            model_name="organisation",
            name="membership_renewal_date_day",
            field=models.IntegerField(
                blank=True,
                default=1,
                null=True,
                validators=[
                    django.core.validators.MaxValueValidator(31),
                    django.core.validators.MinValueValidator(1),
                ],
                verbose_name="Membership Renewal Date - Day",
            ),
        ),
        migrations.AddField(
            model_name="organisation",
            name="membership_renewal_date_month",
            field=models.IntegerField(
                blank=True,
                default=1,
                null=True,
                validators=[
                    django.core.validators.MaxValueValidator(12),
                    django.core.validators.MinValueValidator(1),
                ],
                verbose_name="Membership Renewal Date - Month",
            ),
        ),
        migrations.AlterField(
            model_name="membershiptype",
            name="description",
            field=models.TextField(blank=True, null=True, verbose_name="Description"),
        ),
        migrations.AlterField(
            model_name="membershiptype",
            name="does_not_pay_session_fees",
            field=models.BooleanField(
                default=False, verbose_name="Play Normal Sessions for Free"
            ),
        ),
        migrations.AlterField(
            model_name="membershiptype",
            name="does_not_renew",
            field=models.BooleanField(default=False, verbose_name="Never Expires"),
        ),
        migrations.AlterField(
            model_name="membershiptype",
            name="name",
            field=models.CharField(max_length=20, verbose_name="Name of Membership"),
        ),
        migrations.AlterField(
            model_name="membershiptype",
            name="part_year_fee",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Part Year Fee (for joining later in year)",
            ),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="bank_bsb",
            field=models.CharField(
                blank=True,
                max_length=7,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="BSB must be exactly 6 numbers long.", regex="^\\d{6}$"
                    )
                ],
                verbose_name="BSB Number",
            ),
        ),
    ]
