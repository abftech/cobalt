# Generated by Django 3.2.4 on 2021-09-05 01:36

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("utils", "0004_auto_20201109_1002"),
    ]

    operations = [
        migrations.CreateModel(
            name="Lock",
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
                ("topic", models.CharField(max_length=100, unique=True)),
                (
                    "lock_created_time",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("lock_open_time", models.DateTimeField()),
                ("owner", models.CharField(max_length=200)),
            ],
        ),
    ]
