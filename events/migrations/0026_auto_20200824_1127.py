# Generated by Django 3.0.9 on 2020-08-24 01:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0025_congress_early_payment_discount_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="congress",
            name="allow_youth_payment_discount",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="congress",
            name="youth_payment_discount_age",
            field=models.IntegerField(default=30, verbose_name="Cut off age"),
        ),
        migrations.AddField(
            model_name="congress",
            name="youth_payment_discount_date",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Date for age check"
            ),
        ),
    ]
