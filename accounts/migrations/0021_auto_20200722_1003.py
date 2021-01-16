# Generated by Django 2.2.13 on 2020-07-22 00:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_remove_user_headline"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="receive_sms_results",
            field=models.BooleanField(
                default=False, verbose_name="Receive SMS Results"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="about",
            field=models.TextField(
                blank=True, max_length=800, null=True, verbose_name="About Me"
            ),
        ),
    ]
