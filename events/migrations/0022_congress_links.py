# Generated by Django 3.0.9 on 2020-08-20 12:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0021_auto_20200820_1620"),
    ]

    operations = [
        migrations.AddField(
            model_name="congress",
            name="links",
            field=models.TextField(blank=True, null=True, verbose_name="Links"),
        ),
    ]
