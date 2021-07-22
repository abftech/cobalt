import psycopg2
from django.apps import AppConfig
from django.db import ProgrammingError


class NotificationsConfig(AppConfig):
    name = "notifications"

    def ready(self):
        """Called when Django starts up

        We use the model EmailThread to record what email threads are running.
        After a restart we clear the table.

        For more information look in the docs at notifications_overview

        """

        # Can't import at top of file - Django won't be ready yet
        # Also if this is a clean install migrate won't have been run so catch an error and ignore

        try:
            from .models import EmailThread

            EmailThread.objects.all().delete()
        except Exception as e:
            print(e)
