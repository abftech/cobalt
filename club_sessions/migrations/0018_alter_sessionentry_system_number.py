# Generated by Django 3.2.13 on 2022-05-20 04:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0017_auto_20220520_1421"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sessionentry",
            name="system_number",
            field=models.IntegerField(),
        ),
    ]