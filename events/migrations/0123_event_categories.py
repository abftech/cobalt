import django.contrib.postgres.fields
from django.db import migrations, models

EVENT_TYPE_TO_CODE = {
    "Open": "O",
    "Restricted": "R",
    "Novice": "N",
    "Senior": "S",
    "Youth": "Y",
    "Rookies": "K",
    "Veterans": "V",
    "Womens": "F",
    "Intermediate": "I",
    "Mixed": "X",
}


def migrate_event_type_to_categories(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    for event in Event.objects.all():
        code = EVENT_TYPE_TO_CODE.get(event.event_type, "O")
        event.event_categories = [code]
        event.save(update_fields=["event_categories"])


def reverse_migrate(apps, schema_editor):
    """Reverse: copy first category code back to event_type (best effort)."""
    CODE_TO_TYPE = {v: k for k, v in EVENT_TYPE_TO_CODE.items()}
    Event = apps.get_model("events", "Event")
    for event in Event.objects.all():
        cats = event.event_categories or []
        code = cats[0] if cats else "O"
        event.event_type = CODE_TO_TYPE.get(code, "Open")
        event.save(update_fields=["event_type"])


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0122_alter_evententry_free_format_answer"),
    ]

    operations = [
        # Phase 1: add new field
        migrations.AddField(
            model_name="event",
            name="event_categories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=1),
                blank=True,
                default=list,
                size=None,
                verbose_name="Event Categories",
            ),
        ),
        # Phase 2: copy data
        migrations.RunPython(
            migrate_event_type_to_categories,
            reverse_code=reverse_migrate,
        ),
        # Phase 3: remove old field
        migrations.RemoveField(
            model_name="event",
            name="event_type",
        ),
    ]
