# Generated by Django 3.2.4 on 2021-08-26 04:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0025_alter_memberclubemail_email"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="memberclubemail",
            unique_together={("organisation", "system_number")},
        ),
    ]
