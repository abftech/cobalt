# Generated by Django 3.2.19 on 2024-02-02 23:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0037_realtimenotificationheader_sender_identification"),
    ]

    operations = [
        migrations.AddField(
            model_name="snooper",
            name="limited_notifications",
            field=models.BooleanField(
                default=False, verbose_name="Limited Notifications"
            ),
        ),
    ]
