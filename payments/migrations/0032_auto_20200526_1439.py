# Generated by Django 2.2.12 on 2020-05-26 04:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0031_auto_20200526_1214'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stripetransaction',
            name='member',
            field=models.ForeignKey(blank=True, help_text='User object associated with this transaction', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='main_member', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='stripetransaction',
            name='status',
            field=models.CharField(choices=[('Intent', 'Intent - received customer intent to pay from Stripe'), ('Complete', 'Success - payment completed successfully'), ('Failed', 'Failed - payment failed')], default='Initiated', max_length=9, verbose_name='Status'),
        ),
    ]
