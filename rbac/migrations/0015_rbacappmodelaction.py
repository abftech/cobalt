# Generated by Django 2.2.12 on 2020-06-03 04:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0014_auto_20200603_1111'),
    ]

    operations = [
        migrations.CreateModel(
            name='RBACAppModelAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app', models.CharField(max_length=15)),
                ('model', models.CharField(max_length=15)),
                ('valid_action', models.CharField(max_length=15)),
            ],
        ),
    ]
