# Generated by Django 3.0.9 on 2021-02-17 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0085_auto_20210115_0510'),
    ]

    operations = [
        migrations.AddField(
            model_name='evententry',
            name='comment',
            field=models.TextField(blank=True, null=True, verbose_name='Comments'),
        ),
        migrations.AddField(
            model_name='evententryplayer',
            name='player_comment',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Comment'),
        ),
        migrations.AlterField(
            model_name='congress',
            name='youth_payment_discount_age',
            field=models.IntegerField(default=26, verbose_name='Cut off age'),
        ),
    ]
