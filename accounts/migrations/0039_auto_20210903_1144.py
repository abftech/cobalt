# Generated by Django 3.2.4 on 2021-09-03 01:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0038_auto_20210826_1401"),
    ]

    operations = [
        migrations.AlterField(
            model_name="unregistereduser",
            name="first_name",
            field=models.CharField(
                blank=True, max_length=150, null=True, verbose_name="First Name"
            ),
        ),
        migrations.AlterField(
            model_name="unregistereduser",
            name="last_name",
            field=models.CharField(
                blank=True, max_length=150, null=True, verbose_name="Last Name"
            ),
        ),
        migrations.AlterField(
            model_name="unregistereduser",
            name="origin",
            field=models.CharField(
                choices=[
                    ("MPC", "Masterpoints Centre Import"),
                    ("Pianola", "Pianola Import"),
                    ("CSV", "CSV Import"),
                    ("Manual", "Manual Entry"),
                ],
                max_length=10,
                verbose_name="Origin",
            ),
        ),
    ]
