# Generated by Django 3.2.13 on 2022-05-02 23:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="playersummaryresult",
            name="organisation",
        ),
    ]
