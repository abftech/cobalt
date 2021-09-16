# Generated by Django 3.2.4 on 2021-09-11 02:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0017_auto_20210825_1018"),
    ]

    operations = [
        migrations.CreateModel(
            name="BatchID",
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
                    "batch_id",
                    models.CharField(
                        blank=True, max_length=14, null=True, verbose_name="Batch Id"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EmailBatchRBAC",
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
                ("rbac_role", models.CharField(max_length=300)),
                (
                    "batch_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="notifications.batchid",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="snooper",
            name="batch_id",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="notifications.batchid",
            ),
        ),
    ]