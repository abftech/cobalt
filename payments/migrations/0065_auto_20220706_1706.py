# Generated by Django 3.2.13 on 2022-07-06 07:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0064_auto_20211009_1824"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userpendingpayment",
            name="user",
        ),
        migrations.AddField(
            model_name="userpendingpayment",
            name="system_number",
            field=models.IntegerField(default=0, verbose_name="ABF Number"),
            preserve_default=False,
        ),
    ]
