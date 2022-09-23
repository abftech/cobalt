# Generated by Django 3.2.15 on 2022-09-23 00:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("logs", "0008_auto_20210707_0957"),
    ]

    operations = [
        migrations.AddField(
            model_name="log",
            name="user_object",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="ip",
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name="log",
            name="message",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="log",
            name="severity",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DEBUG", "Level 0 - Debug"),
                    ("INFO", "Level 1 - Informational"),
                    ("WARN", "Level 2 - Warning"),
                    ("ERROR", "Level 3 - Error"),
                    ("HIGH", "Level 4 - High"),
                    ("CRITICAL", "Level 5 - Critical"),
                ],
                default="INFO",
                max_length=8,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="source",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name="log",
            name="sub_source",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="log",
            name="user",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
