# Generated by Django 3.2.5 on 2021-10-12 21:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0007_auto_20211012_1054"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessiontype",
            name="master_session_type",
            field=models.CharField(
                choices=[
                    ("DP", "Duplicate"),
                    ("MS", "Multi-Session"),
                    ("WS", "Workshop"),
                ],
                default="DP",
                max_length=2,
            ),
        ),
    ]