# Generated by Django 3.2.4 on 2021-08-26 01:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0025_alter_memberclubemail_email"),
        ("accounts", "0036_alter_user_system_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="unregistereduser",
            name="added_by_club",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="added_by_club",
                to="organisations.organisation",
            ),
        ),
        migrations.AlterField(
            model_name="unregistereduser",
            name="email",
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                verbose_name="Email Address (accessible by all clubs)",
            ),
        ),
        migrations.AlterField(
            model_name="unregistereduser",
            name="last_registration_invite_by_club",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="last_registration_invite_by_club",
                to="organisations.organisation",
            ),
        ),
    ]