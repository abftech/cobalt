# Generated by Django 3.0.9 on 2020-12-12 04:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0040_stripelog_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="stripelog",
            name="type",
        ),
        migrations.AddField(
            model_name="stripelog",
            name="cobalt_tran_type",
            field=models.TextField(
                blank=True, null=True, verbose_name="Cobalt Tran Type"
            ),
        ),
        migrations.AddField(
            model_name="stripelog",
            name="event_type",
            field=models.TextField(blank=True, null=True, verbose_name="Event Type"),
        ),
    ]
