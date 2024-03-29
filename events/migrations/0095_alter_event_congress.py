# Generated by Django 3.2.4 on 2021-06-25 23:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0094_alter_event_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="congress",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="events.congress"
            ),
        ),
    ]
