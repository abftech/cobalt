# Generated by Django 3.0.9 on 2020-12-16 04:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0078_auto_20201202_1115'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventlog',
            name='action',
            field=models.TextField(verbose_name='Action'),
        ),
    ]
