# Generated by Django 3.2.10 on 2022-03-29 01:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0038_alter_organisation_suburb"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisation",
            name="suburb",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]