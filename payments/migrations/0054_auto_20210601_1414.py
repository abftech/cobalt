# Generated by Django 3.0.9 on 2021-06-01 04:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0053_auto_20210601_1400"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stripetransaction",
            name="refund_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                max_digits=12,
                verbose_name="Refund Amount",
            ),
        ),
    ]
