# Generated by Django 3.2.19 on 2024-08-06 04:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0070_memberclubdetails_left_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="memberclubdetails",
            name="previous_membership_status",
            field=models.CharField(
                blank=True,
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
                default=None,
                max_length=4,
                null=True,
                verbose_name="Previous Membership Status",
            ),
        ),
    ]
