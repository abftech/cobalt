# Generated by Django 2.1 on 2020-04-28 00:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='address1',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='address2',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='address3',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
