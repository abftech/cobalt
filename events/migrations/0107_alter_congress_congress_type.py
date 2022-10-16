# Generated by Django 3.2.15 on 2022-10-16 23:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0106_auto_20220817_1006"),
    ]

    operations = [
        migrations.AlterField(
            model_name="congress",
            name="congress_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("national_gold", "National gold point"),
                    ("state_championship", "State championship"),
                    ("state_congress", "State congress"),
                    ("state_event", "State event"),
                    ("club_congress", "Club congress"),
                    ("club", "Club event"),
                    ("lesson", "Lesson"),
                    ("other", "Other"),
                ],
                max_length=30,
                null=True,
                verbose_name="Congress Type",
            ),
        ),
    ]
