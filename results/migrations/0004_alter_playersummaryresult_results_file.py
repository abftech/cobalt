# Generated by Django 3.2.10 on 2022-05-03 00:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0003_alter_playersummaryresult_result_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="playersummaryresult",
            name="results_file",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="results.resultsfile"
            ),
        ),
    ]
