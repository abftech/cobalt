# Generated by Django 3.2.13 on 2022-06-05 22:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0005_resultsfile_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="playersummaryresult",
            name="partner_or_team_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
