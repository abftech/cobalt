# Generated by Django 2.1 on 2020-05-19 02:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_auto_20200510_1402"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="stripe_auto_confirmed",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
