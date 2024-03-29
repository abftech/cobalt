# Generated by Django 3.2.4 on 2021-06-26 11:10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Incident",
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
                ("reported_by_email", models.TextField(blank=True, null=True)),
                ("description", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Unassigned", "Unassigned to anyone"),
                            ("In Progress", "In Progress and assigned to someone"),
                            ("Pending User Feedback", "Awaiting feedback from user"),
                            ("Closed", "Closed"),
                        ],
                        default="Unassigned",
                        max_length=30,
                    ),
                ),
                (
                    "incident_type",
                    models.CharField(
                        choices=[
                            ("Security", "Security Problem"),
                            ("Congress Entry", "Congress Entry Problem"),
                            ("Other", "Other"),
                        ],
                        default="Other",
                        max_length=30,
                    ),
                ),
                (
                    "created_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Created Date"
                    ),
                ),
                (
                    "closed_date",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Closed Date"
                    ),
                ),
                (
                    "reported_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
