# Generated by Django 3.0.9 on 2020-12-21 03:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0080_evententry_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evententry",
            name="notes",
            field=models.TextField(
                blank=True, max_length=100, null=True, verbose_name="Notes"
            ),
        ),
    ]
