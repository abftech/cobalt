# Generated by Django 3.0.9 on 2020-11-10 03:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0073_congress_latest"),
    ]

    operations = [
        migrations.RenameField(
            model_name="congress",
            old_name="latest",
            new_name="latest_news",
        ),
    ]
