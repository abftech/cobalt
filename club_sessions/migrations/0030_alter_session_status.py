# Generated by Django 3.2.13 on 2022-09-05 07:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0029_session_import_messages"),
    ]

    operations = [
        migrations.AlterField(
            model_name="session",
            name="status",
            field=models.CharField(
                choices=[
                    ("LD", "Data Loaded"),
                    ("BC", "Credits Processed"),
                    ("CO", "Complete"),
                ],
                default="LD",
                max_length=2,
            ),
        ),
    ]
