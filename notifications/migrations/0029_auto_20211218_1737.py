# Generated by Django 3.2.10 on 2021-12-18 06:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0028_auto_20211218_1724"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="realtimenotificationheader",
            name="message",
        ),
        migrations.AddField(
            model_name="realtimenotificationheader",
            name="invalid_lines",
            field=models.TextField(blank=True, null=True),
        ),
    ]
