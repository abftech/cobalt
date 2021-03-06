# Generated by Django 2.1 on 2020-04-29 01:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0004_auto_20200428_1116'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0016_auto_20200429_1050'),
    ]

    operations = [
        migrations.AddField(
            model_name='membertransaction',
            name='organisation',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='organisations.Organisation'),
        ),
        migrations.AddField(
            model_name='membertransaction',
            name='other_member',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='other_member', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='membertransaction',
            name='member',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_member', to=settings.AUTH_USER_MODEL),
        ),
    ]
