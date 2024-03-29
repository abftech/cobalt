# Generated by Django 3.2.12 on 2022-04-15 23:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organisations", "0047_alter_welcomepack_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="welcomepack",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="welcomepack",
            name="last_modified_by",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="welcome_pack_last_modified_by",
                to="accounts.user",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="welcomepack",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
