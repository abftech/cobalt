# Generated by Django 3.2.10 on 2021-12-14 21:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0024_realtimenotification_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="RealtimeNotificationHeader",
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
                ("description", models.TextField()),
                ("attempted_send_number", models.IntegerField(default=0)),
                ("created_time", models.DateTimeField(auto_now_add=True)),
                (
                    "admin",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="realtimenotification",
            name="header",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="notifications.realtimenotificationheader",
            ),
        ),
    ]
