# Generated by Django 3.2.5 on 2021-11-01 23:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0036_rename_miscpaytypes_miscpaytype'),
        ('club_sessions', '0009_alter_sessiontypepaymentmethodmembership_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='time_of_day',
            field=models.CharField(blank=True, choices=[('AM', 'Morning'), ('PM', 'Afternoon'), ('EV', 'Evening')], max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='session',
            name='venue',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='organisations.orgvenue'),
        ),
    ]
