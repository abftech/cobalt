# Generated by Django 3.2.10 on 2022-04-12 00:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0041_auto_20220408_1302"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orgemailtemplate",
            name="banner",
            field=models.ImageField(
                default="email_banners/default_banner.jpg", upload_to="email_banners/"
            ),
        ),
    ]
