# Generated by Django 3.2.15 on 2023-01-13 07:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0109_alter_congress_congress_venue_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="congress",
            name="do_not_auto_close_congress",
            field=models.BooleanField(default=False),
        ),
    ]
