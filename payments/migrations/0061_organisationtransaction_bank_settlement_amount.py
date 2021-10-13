# Generated by Django 3.2.4 on 2021-09-28 04:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0060_alter_organisationtransaction_organisation"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisationtransaction",
            name="bank_settlement_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name="Bank Settlement Amount",
            ),
        ),
    ]