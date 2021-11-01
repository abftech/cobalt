# Generated by Django 3.2.5 on 2021-10-10 01:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0004_alter_sessionentry_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessiontype",
            name="master_session_type",
            field=models.CharField(
                choices=[
                    ("DP", "Duplicate"),
                    ("MS", "Multi-session"),
                    ("WS", "Workshop"),
                ],
                default="DP",
                max_length=2,
            ),
        ),
    ]