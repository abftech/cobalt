# Generated by Django 3.2.15 on 2022-09-21 04:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0032_auto_20220919_1342"),
    ]

    operations = [
        migrations.AlterField(
            model_name="session",
            name="description",
            field=models.CharField(max_length=50),
        ),
    ]
