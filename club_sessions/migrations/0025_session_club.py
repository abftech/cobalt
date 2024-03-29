# Generated by Django 3.2.15 on 2022-09-01 23:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0059_organisation_results_email_message"),
        ("club_sessions", "0024_session_additional_session_fee_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="club",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="organisations.organisation",
            ),
            preserve_default=False,
        ),
    ]
