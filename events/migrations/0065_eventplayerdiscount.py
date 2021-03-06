# Generated by Django 3.0.9 on 2020-10-25 03:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0064_auto_20201023_0646'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventPlayerDiscount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_fee', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Entry Fee')),
                ('reason', models.CharField(max_length=200, verbose_name='Reason')),
                ('create_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_discount', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.Event')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='player_discount', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
