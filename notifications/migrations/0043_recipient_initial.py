# Generated by Django 3.2.19 on 2024-03-12 20:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0042_recipient_include"),
    ]

    operations = [
        migrations.AddField(
            model_name="recipient",
            name="initial",
            field=models.BooleanField(default=True, verbose_name="Initial Selection"),
        ),
    ]