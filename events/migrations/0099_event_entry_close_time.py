# Generated by Django 3.2.5 on 2021-11-06 02:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0098_alter_event_entry_youth_payment_discount"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="entry_close_time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]