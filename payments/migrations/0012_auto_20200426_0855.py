# Generated by Django 2.1 on 2020-04-25 22:55

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0011_auto_20200425_1519'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AutoTopUp',
            new_name='AutoTopUpConfig',
        ),
    ]
