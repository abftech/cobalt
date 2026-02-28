"""Cron job to delete old notifications"""

import logging

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Email, InAppNotification
from utils.models import BatchStatus

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Running delete_old_in_app_notifications")

        batch = BatchStatus.objects.create(command="delete_old_in_app_notifications")
        summary_lines = []

        try:
            three_months_ago = timezone.now() - relativedelta(months=3)
            notifications = InAppNotification.objects.filter(
                created_date__lt=three_months_ago
            )
            count = len(notifications)
            logger.info(f"Deleting {count} InAppNotifications.")
            notifications.delete()
            summary_lines.append(
                f"{count} in-app notification(s) deleted (older than 3 months)"
            )
        except Exception as e:
            logger.exception(
                "delete_old_in_app_notifications failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("delete_old_in_app_notifications finished")
