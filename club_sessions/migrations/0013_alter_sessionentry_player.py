# Generated by Django 3.2.12 on 2022-05-19 05:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0012_alter_session_time_of_day"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessionentry",
            name="player",
            field=models.PositiveIntegerField(),
        ),
    ]
