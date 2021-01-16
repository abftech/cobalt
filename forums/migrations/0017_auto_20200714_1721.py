# Generated by Django 3.0.8 on 2020-07-14 07:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forums", "0016_auto_20200714_1454"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment1",
            name="last_changed_by",
            field=models.CharField(
                blank=True, max_length=50, null=True, verbose_name="Last Changed By"
            ),
        ),
        migrations.AddField(
            model_name="comment2",
            name="last_changed_by",
            field=models.CharField(
                blank=True, max_length=50, null=True, verbose_name="Last Changed By"
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="last_changed_by",
            field=models.CharField(
                blank=True, max_length=50, null=True, verbose_name="Last Changed By"
            ),
        ),
    ]
