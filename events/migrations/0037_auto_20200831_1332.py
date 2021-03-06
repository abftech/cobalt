# Generated by Django 3.0.9 on 2020-08-31 03:32

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0036_evententryplayer_entry_fee"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="entry_complete_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="first_created_date",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
