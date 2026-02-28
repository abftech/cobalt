import logging

from django.core.management.base import BaseCommand

from support.helpdesk import close_old_tickets
from utils.models import BatchStatus

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Running close_old_helpdesk_tickets")

        batch = BatchStatus.objects.create(command="close_old_helpdesk_tickets")
        summary_lines = []

        try:
            tickets_closed = close_old_tickets()
            summary_lines.append(f"{tickets_closed} ticket(s) automatically closed")
        except Exception as e:
            logger.exception(
                "close_old_helpdesk_tickets failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("close_old_helpdesk_tickets finished")
