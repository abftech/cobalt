# Generated by Django 3.2.19 on 2024-04-01 02:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0047_auto_20240328_1444"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="recipient",
            unique_together={("batch", "system_number")},
        ),
    ]
