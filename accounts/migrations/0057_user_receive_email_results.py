# Generated by Django 3.2.15 on 2023-02-10 04:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0056_auto_20221014_0533"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="receive_email_results",
            field=models.BooleanField(
                default=True, verbose_name="Receive Results by Email"
            ),
        ),
    ]
