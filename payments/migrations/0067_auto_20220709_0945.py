# Generated by Django 3.2.13 on 2022-07-08 23:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0066_userpendingpayment_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisationtransaction",
            name="club_session_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="MemberOrganisationLink",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "member_transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="payments.membertransaction",
                    ),
                ),
                (
                    "organisation_transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="payments.organisationtransaction",
                    ),
                ),
            ],
        ),
    ]
