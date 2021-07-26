# Generated by Django 3.2.4 on 2021-07-26 01:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0010_auto_20200801_1426"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="organisations.organisation",
            ),
        ),
    ]
