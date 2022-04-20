# Generated by Django 3.2.12 on 2022-04-18 10:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0048_auto_20220416_0935"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0032_realtimenotification_has_been_read"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailAttachment",
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
                ("attachment", models.FileField(upload_to="attachments")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "member",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachment_member",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachment_org",
                        to="organisations.organisation",
                    ),
                ),
            ],
        ),
    ]