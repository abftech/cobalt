# Generated by Django 3.2.13 on 2022-05-02 22:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import results.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organisations", "0048_auto_20220416_0935"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ResultsFile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "results_file",
                    models.FileField(
                        upload_to=results.models._results_file_directory_path
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("PU", "Published"), ("PE", "Pending")],
                        default="PE",
                        max_length=2,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="organisations.organisation",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PlayerSummaryResult",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("player_system_number", models.PositiveIntegerField()),
                ("result_date", models.DateTimeField()),
                ("position", models.PositiveIntegerField(blank=True, null=True)),
                ("percentage", models.FloatField(blank=True, null=True)),
                (
                    "result_string",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                ("event_name", models.CharField(blank=True, max_length=200, null=True)),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="organisations.organisation",
                    ),
                ),
                (
                    "results_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="results.resultsfile",
                    ),
                ),
            ],
        ),
    ]
