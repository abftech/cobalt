# Generated by Django 3.2.10 on 2021-12-17 04:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0026_auto_20211215_0918"),
    ]

    operations = [
        migrations.AddField(
            model_name="realtimenotificationheader",
            name="successful_send_number",
            field=models.IntegerField(default=0),
        ),
    ]
