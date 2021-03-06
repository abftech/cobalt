# Generated by Django 2.1 on 2020-05-02 00:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0004_auto_20200428_1116'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='address1',
            field=models.CharField(blank='True', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='address2',
            field=models.CharField(blank='True', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='postcode',
            field=models.CharField(blank='True', max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='state',
            field=models.CharField(blank='True', max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='suburb',
            field=models.CharField(blank='True', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='type',
            field=models.CharField(blank='True', choices=[('Club', 'Bridge Club'), ('State', 'State Association'), ('National', 'National Body'), ('Other', 'Other')], max_length=8, null=True),
        ),
    ]
