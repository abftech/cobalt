# Generated by Django 3.2.15 on 2023-03-06 00:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0075_auto_20230120_1653"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisationtransaction",
            name="gl_series",
            field=models.PositiveIntegerField(blank=True, default=0, null=True),
        ),
    ]
