# Generated by Django 3.2.4 on 2021-07-26 08:48

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0011_organisation_parent"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="organisation",
            name="parent",
        ),
        migrations.AddField(
            model_name="organisation",
            name="club_email",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name="organisation",
            name="club_website",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="address1",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Address Line 1"
            ),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="address2",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Address Line 2"
            ),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="bank_account",
            field=models.CharField(
                blank=True,
                max_length=14,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Account number must contain only digits and dashes",
                        regex="^[0-9-]*$",
                    )
                ],
                verbose_name="Bank Account Number",
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
                        message="BSB must be entered in the format: '999-999'.",
                        regex="^\\d{3}-\\d{3}$",
                    )
                ],
                verbose_name="BSB Number",
            ),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="postcode",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="state",
            field=models.CharField(blank=True, max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="suburb",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Club", "Bridge Club"),
                    ("State", "State Association"),
                    ("National", "National Body"),
                    ("Other", "Other"),
                ],
                max_length=8,
                null=True,
            ),
        ),
    ]
