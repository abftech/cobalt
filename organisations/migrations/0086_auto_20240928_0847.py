# Generated by Django 3.2.19 on 2024-09-27 22:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0085_alter_membershiptype_grace_period_days"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="memberclubdetails",
            options={"verbose_name_plural": "Member Club Details"},
        ),
        migrations.AlterModelOptions(
            name="membercluboptions",
            options={"verbose_name_plural": "Member Club Options"},
        ),
    ]
