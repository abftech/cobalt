# Generated by Django 2.2.13 on 2020-07-21 00:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_auto_20200709_1536"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="headline",),
    ]
