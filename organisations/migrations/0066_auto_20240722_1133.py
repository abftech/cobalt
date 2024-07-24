# Generated by Django 3.2.19 on 2024-07-22 01:33

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import organisations.models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0065_alter_orgemailtemplate_banner"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="membershiptype",
            name="part_year_fee",
        ),
        migrations.RemoveField(
            model_name="organisation",
            name="membership_part_year_date_day",
        ),
        migrations.RemoveField(
            model_name="organisation",
            name="membership_part_year_date_month",
        ),
        migrations.AddField(
            model_name="membermembershiptype",
            name="due_date",
            field=models.DateField(
                blank=True, default=None, null=True, verbose_name="Payment due date"
            ),
        ),
        migrations.AddField(
            model_name="membermembershiptype",
            name="end_date",
            field=models.DateField(
                blank=True, default=None, null=True, verbose_name="Ends At"
            ),
        ),
        migrations.AddField(
            model_name="membermembershiptype",
            name="fee",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Fee",
            ),
        ),
        migrations.AddField(
            model_name="membermembershiptype",
            name="membership_state",
            field=models.CharField(
                choices=[
                    ("CUR", "Current"),
                    ("DUE", "Due"),
                    ("END", "Ended"),
                    ("LAP", "Lapsed"),
                    ("RES", "Resigned"),
                    ("TRM", "Terminated"),
                    ("DEC", "Deceased"),
                ],
                default="CUR",
                max_length=4,
                verbose_name="State",
            ),
        ),
        migrations.AddField(
            model_name="membermembershiptype",
            name="paid_until_date",
            field=models.DateField(
                blank=True, default=None, null=True, verbose_name="Paid Until"
            ),
        ),
        migrations.AddField(
            model_name="membershiptype",
            name="grace_period_days",
            field=models.IntegerField(
                default=31, verbose_name="Payment Grace Period (days)"
            ),
        ),
        migrations.AddField(
            model_name="organisation",
            name="full_club_admin",
            field=models.BooleanField(
                default=False, verbose_name="Use full club admin"
            ),
        ),
        migrations.AlterField(
            model_name="membermembershiptype",
            name="membership_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="organisations.membershiptype",
            ),
        ),
        migrations.CreateModel(
            name="MemberClubDetails",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("system_number", models.IntegerField(verbose_name="ABF Number")),
                (
                    "membership_status",
                    models.CharField(
                        choices=[
                            ("CUR", "Current"),
                            ("DUE", "Due"),
                            ("END", "Ended"),
                            ("LAP", "Lapsed"),
                            ("RES", "Resigned"),
                            ("TRM", "Terminated"),
                            ("DEC", "Deceased"),
                            ("CON", "Contact"),
                        ],
                        default="CUR",
                        max_length=4,
                        verbose_name="Membership Status",
                    ),
                ),
                (
                    "joined_date",
                    models.DateField(blank=True, null=True, verbose_name="Date Joined"),
                ),
                (
                    "address1",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Address Line 1",
                    ),
                ),
                (
                    "address2",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Address Line 2",
                    ),
                ),
                ("state", models.CharField(blank=True, max_length=3, null=True)),
                ("postcode", models.CharField(blank=True, max_length=10, null=True)),
                (
                    "mobile",
                    models.CharField(
                        blank=True,
                        max_length=15,
                        null=True,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="We only accept Australian phone numbers starting 04 which are 10 numbers long.",
                                regex="^04\\d{8}$",
                            )
                        ],
                        verbose_name="Mobile Number",
                    ),
                ),
                (
                    "other_phone",
                    models.CharField(
                        blank=True,
                        max_length=15,
                        null=True,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="We only accept Australian phone numbers with 8 or 10 digits.",
                                regex="^(\\d{8}|\\d{10})$",
                            )
                        ],
                        verbose_name="Phone",
                    ),
                ),
                (
                    "dob",
                    models.DateField(
                        blank="True",
                        null=True,
                        validators=[organisations.models.no_future],
                    ),
                ),
                (
                    "club_membership_number",
                    models.CharField(blank=True, max_length=15, null=True),
                ),
                (
                    "emergency_contact",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        null=True,
                        verbose_name="Emergency Contact",
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        max_length=254,
                        null=True,
                        verbose_name="Email for your club only",
                    ),
                ),
                ("email_hard_bounce", models.BooleanField(default=False)),
                ("email_hard_bounce_reason", models.TextField(blank=True, null=True)),
                ("email_hard_bounce_date", models.DateTimeField(blank=True, null=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="organisations.organisation",
                    ),
                ),
                (
                    "latest_membership",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="organisations.membershiptype",
                    ),
                ),
            ],
            options={
                "unique_together": {("club", "system_number")},
            },
        ),
    ]
