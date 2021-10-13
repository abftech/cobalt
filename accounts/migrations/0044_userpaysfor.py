# Generated by Django 3.2.5 on 2021-10-08 01:12

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0043_user_covid_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPaysFor",
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
                    "criterion",
                    models.CharField(
                        choices=[
                            ("AL", "Always"),
                            ("PT", "If Playing Together"),
                            ("PS", "If Playing Same Session"),
                        ],
                        default="AL",
                        max_length=2,
                    ),
                ),
                (
                    "lucky_person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lucky_person",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "sponsor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sponsor",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]