# Generated by Django 3.2.13 on 2022-06-14 20:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0049_alter_membermembershiptype_unique_together"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="membermembershiptype",
            unique_together=set(),
        ),
    ]
