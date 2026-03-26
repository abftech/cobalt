from django.db import migrations


class Migration(migrations.Migration):
    # CONCURRENTLY cannot run inside a transaction
    atomic = False

    dependencies = [
        ("notifications", "0055_alter_unregisteredblockedemail_un_registered_user"),
    ]

    operations = [
        # Add an index on post_office_email.message_id.
        # Every SNS webhook event handler does:
        #     PostOfficeEmail.objects.get(message_id=message_id)
        # The django-post-office Email model has no db_index on this field, so
        # without this index every webhook triggers a full table scan. As the
        # post_office_email table grows this causes the 10-second webhook latency
        # seen in production.
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_office_email_message_id
            ON post_office_email (message_id);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_post_office_email_message_id;
            """,
        ),
    ]
