# Generated by Django 3.2.15 on 2023-04-10 02:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0115_auto_20230406_0945"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="congress",
            name="automatically_mark_club_pp_as_paid",
        ),
    ]
