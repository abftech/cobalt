# Generated by Django 3.2.15 on 2022-10-05 22:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0034_auto_20220926_0539"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="director_notes",
            field=models.TextField(blank=True, null=True),
        ),
    ]
