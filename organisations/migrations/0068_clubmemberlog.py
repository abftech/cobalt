# Generated by Django 3.2.19 on 2024-07-24 03:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organisations", "0067_alter_memberclubdetails_latest_membership"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClubMemberLog",
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
                ("system_number", models.IntegerField(verbose_name="System number")),
                ("date", models.DateTimeField(auto_now_add=True)),
                ("description", models.TextField(verbose_name="Description")),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="organisations.organisation",
                    ),
                ),
            ],
            options={
                "ordering": ["-date"],
            },
        ),
    ]
