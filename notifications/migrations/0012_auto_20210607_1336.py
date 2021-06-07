# Generated by Django 3.2.4 on 2021-06-07 03:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0011_auto_20201218_1244"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailThread",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Create Date"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="abstractemail",
            name="batch_id",
            field=models.CharField(
                blank=True, max_length=14, null=True, verbose_name="Batch Id"
            ),
        ),
        migrations.AlterField(
            model_name="abstractemail",
            name="member",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="member",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
