# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0009_resultsfile_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resultsfile",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("MP_PAIRS", "MP Pairs"),
                    ("CROSS_IMP", "Cross IMP"),
                    ("BUTLER_PAIRS", "Butler Pairs"),
                ],
                default="MP_PAIRS",
                max_length=20,
            ),
        ),
    ]
