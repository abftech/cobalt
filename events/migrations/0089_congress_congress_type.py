# Generated by Django 3.0.9 on 2021-05-06 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0088_auto_20210424_2051'),
    ]

    operations = [
        migrations.AddField(
            model_name='congress',
            name='congress_type',
            field=models.CharField(blank=True, choices=[('national_gold', 'National gold point event'), ('state_championship', 'State championship event'), ('state_congress', 'State congress event'), ('club', 'Club event'), ('club_congress', 'Club congress'), ('other', 'Other event')], max_length=30, null=True, verbose_name='Congress Type'),
        ),
    ]
