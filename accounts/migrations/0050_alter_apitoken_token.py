# Generated by Django 3.2.10 on 2021-12-14 02:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0049_alter_apitoken_token"),
    ]

    operations = [
        migrations.AlterField(
            model_name="apitoken",
            name="token",
            field=models.CharField(
                default="Overridden on save",
                help_text="This is set when you first save it",
                max_length=40,
            ),
        ),
    ]
