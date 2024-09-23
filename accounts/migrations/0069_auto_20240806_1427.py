# Generated by Django 3.2.19 on 2024-08-06 04:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0068_useradditionalinfo_member_sort_order"),
    ]

    operations = [
        migrations.CreateModel(
            name="NextInternalSystemNumber",
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
                (
                    "number",
                    models.IntegerField(
                        default=1000000000, verbose_name="Next Internal System Number"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="unregistereduser",
            name="internal_system_number",
            field=models.BooleanField(default=False),
        ),
    ]