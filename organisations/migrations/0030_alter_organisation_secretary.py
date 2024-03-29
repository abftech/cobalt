# Generated by Django 3.2.4 on 2021-09-06 02:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organisations", "0029_clubtag_memberclubtag_visitor"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisation",
            name="secretary",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="secretary",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
