# Generated by Django 3.2.15 on 2023-04-05 23:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0114_alter_evententry_entry_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="congress",
            name="automatically_mark_non_bridge_credits_as_paid",
        ),
        migrations.AddField(
            model_name="congress",
            name="automatically_mark_club_pp_as_paid",
            field=models.BooleanField(default=True),
        ),
    ]
