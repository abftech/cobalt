# Generated by Django 3.2.10 on 2022-05-25 01:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0018_alter_sessionentry_system_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionentry",
            name="fee",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]
