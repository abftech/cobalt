# Generated by Django 3.2.12 on 2022-04-19 10:20

from django.db import migrations, models
import notifications.models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0033_emailattachment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailattachment",
            name="attachment",
            field=models.FileField(
                upload_to=notifications.models._email_attachment_directory_path
            ),
        ),
    ]
