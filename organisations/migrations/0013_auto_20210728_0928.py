# Generated by Django 3.2.4 on 2021-07-27 23:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organisations", "0012_auto_20210726_1848"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="secretary",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="secretary",
                to="accounts.user",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="organisation",
            name="last_updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="org_last_updated_by",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
