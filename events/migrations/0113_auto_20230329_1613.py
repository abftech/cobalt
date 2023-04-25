# Generated by Django 3.2.15 on 2023-03-29 05:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0112_alter_congress_online_platform"),
    ]

    operations = [
        migrations.AddField(
            model_name="congress",
            name="automatically_mark_non_bridge_credits_as_paid",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="evententry",
            name="entry_status",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Complete", "Complete"),
                    ("Cancelled", "Cancelled"),
                    ("In Basket", "In Basket"),
                ],
                default="Pending",
                max_length=20,
                verbose_name="Entry Status",
            ),
        ),
    ]