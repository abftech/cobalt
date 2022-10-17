# Generated by Django 3.2.15 on 2022-10-10 04:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("club_sessions", "0035_session_director_notes"),
        ("payments", "0069_auto_20220720_0913"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpendingpayment",
            name="session_misc_payment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="club_sessions.sessionmiscpayment",
            ),
        ),
    ]