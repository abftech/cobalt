# Generated by Django 3.0.8 on 2020-08-06 06:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0009_auto_20200806_1555"),
    ]

    operations = [
        migrations.AddField(
            model_name="congress",
            name="general_info",
            field=models.TextField(default="TBA", verbose_name="General Information"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="congress",
            name="people",
            field=models.TextField(blank=True, null=True, verbose_name="People"),
        ),
        migrations.AddField(
            model_name="congress",
            name="raw_html",
            field=models.TextField(blank=True, null=True, verbose_name="Raw HTML"),
        ),
        migrations.AlterField(
            model_name="congress",
            name="additional_info",
            field=models.TextField(
                blank=True, null=True, verbose_name="Congress Additional Information"
            ),
        ),
        migrations.AlterField(
            model_name="congress",
            name="venue_additional_info",
            field=models.TextField(
                blank=True, null=True, verbose_name="Venue Additional Information"
            ),
        ),
        migrations.AlterField(
            model_name="congress",
            name="venue_catering",
            field=models.TextField(
                blank=True, null=True, verbose_name="Venue Catering"
            ),
        ),
    ]
