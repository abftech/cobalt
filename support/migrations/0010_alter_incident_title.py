# Generated by Django 3.2.4 on 2021-07-02 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("support", "0009_notifyuserbytype"),
    ]

    operations = [
        migrations.AlterField(
            model_name="incident",
            name="title",
            field=models.CharField(max_length=80, verbose_name="Subject"),
        ),
    ]
