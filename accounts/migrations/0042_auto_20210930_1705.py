# Generated by Django 3.2.4 on 2021-09-30 07:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0041_user_admin_covid_confirm"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="admin_covid_confirm",
        ),
        migrations.RemoveField(
            model_name="user",
            name="user_covid_confirm",
        ),
    ]