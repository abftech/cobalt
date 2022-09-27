# Generated by Django 3.2.15 on 2022-09-25 19:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0033_alter_session_description"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sessionentry",
            name="amount_paid",
        ),
        migrations.AddField(
            model_name="sessionentry",
            name="is_paid",
            field=models.BooleanField(default=False),
        ),
    ]