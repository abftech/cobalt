# Generated by Django 3.0.9 on 2021-05-21 10:09

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0089_congress_congress_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='congress',
            name='congress_type',
            field=models.CharField(blank=True, choices=[('national_gold', 'National gold point'), ('state_championship', 'State championship'), ('state_congress', 'State congress'), ('club', 'Club event'), ('club_congress', 'Club congress'), ('other', 'Other')], max_length=30, null=True, verbose_name='Congress Type'),
        ),
        migrations.AlterField(
            model_name='event',
            name='entry_early_payment_discount',
            field=models.DecimalField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=12, null=True, verbose_name='Early Payment Discount'),
        ),
    ]
