# Generated by Django 3.2.4 on 2021-08-14 03:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0021_membermembershiptype_system_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membermembershiptype",
            name="system_number",
            field=models.IntegerField(blank=True, verbose_name="ABF Number"),
        ),
    ]