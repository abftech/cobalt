from django.apps import AppConfig
from django.utils import timezone
import logging

logger = logging.getLogger("cobalt")

logger.info("something")


class NotificationsConfig(AppConfig):
    name = "notifications"

    def ready(self):
        """Called when Django starts up

        For more information look in the docs at notifications_overview

        This handles the signals from django-ses when notifications are received from SES.

        We expect to find two header items that are attached when we sent:
            COBALT_ID - pk of the Django Post Office email
            COBALT_ENV - environment (test, uat, prod)

        BE CAREFUL!!! This can impact production, it is the only part of Cobalt that is
                      shared between all environments.

        """
        # Can't import at top of file - Django won't be ready yet
        from django.dispatch import receiver
        from django_ses.signals import (
            send_received,
            delivery_received,
            open_received,
            click_received,
            bounce_received,
            complaint_received,
        )
        from notifications.models import Snooper
        from post_office.models import Email as PostOfficeEmail
        from logs.views import log_event

        logger.info("inside")

        def _get_message_id(mail_obj):
            """Utility to get the message_id from the message"""

            logger.info("get message id")

            # Get headers from mail_obj - headers is a list of headers
            headers = mail_obj["headers"]

            for header in headers:
                if header["name"] == "Message-ID":
                    return header["value"]

            return None

        @receiver(send_received)
        def send_handler(sender, mail_obj, send_obj, raw_message, *args, **kwargs):
            """Handle SES incoming info"""

            logger.info("inside send handler")

            message_id = _get_message_id(mail_obj)

            logger.info(f"SENT: Received Message-ID: {message_id}")

            print("--- > Inside send_handler", flush=True)

            try:
                post_office_email = PostOfficeEmail.objects.get(message_id=message_id)
                snooper, _ = Snooper.objects.get_or_create(
                    post_office_email=post_office_email
                )
                snooper.ses_sent_at = timezone.now()
                snooper.save()
                logger.info(f"SENT: Processed Message-ID: {message_id}")
            except (AttributeError, PostOfficeEmail.DoesNotExist):
                logger.info(f"SENT: No matching message found for :{message_id}")

        @receiver(delivery_received)
        def delivery_handler(
            sender, mail_obj, delivery_obj, raw_message, *args, **kwargs
        ):
            """Handle SES incoming info"""

            message_id = _get_message_id(mail_obj)

            logger.info(f"DELIVER: Received Message-ID: {message_id}")

            try:
                post_office_email = PostOfficeEmail.objects.get(message_id=message_id)
                snooper, _ = Snooper.objects.get_or_create(
                    post_office_email=post_office_email
                )
                snooper.ses_delivered_at = timezone.now()
                snooper.save()
                logger.info(f"DELIVER: Processed Message-ID: {message_id}")
            except (AttributeError, PostOfficeEmail.DoesNotExist):
                logger.info(f"DELIVER: No matching message found for :{message_id}")

        @receiver(open_received)
        def open_handler(sender, mail_obj, open_obj, raw_message, *args, **kwargs):
            """Handle SES incoming info"""

            message_id = _get_message_id(mail_obj)

            logger.info(f"OPEN: Received Message-ID: {message_id}")

            try:
                post_office_email = PostOfficeEmail.objects.get(message_id=message_id)
                snooper = Snooper.objects.filter(
                    post_office_email=post_office_email
                ).first()
                snooper.ses_last_opened_at = timezone.now()
                snooper.ses_open_count += 1
                snooper.save()
                logger.info(f"OPEN: Processed Message-ID: {message_id}")
            except (AttributeError, PostOfficeEmail.DoesNotExist):
                logger.info(f"OPEN: No matching message found for :{message_id}")

        @receiver(click_received)
        def click_handler(sender, mail_obj, click_obj, raw_message, *args, **kwargs):
            """Handle SES incoming info"""

            message_id = _get_message_id(mail_obj)

            logger.info(f"CLICK: Received Message-ID: {message_id}")

            try:
                post_office_email = PostOfficeEmail.objects.get(message_id=message_id)
                snooper = Snooper.objects.filter(
                    post_office_email=post_office_email
                ).first()
                snooper.ses_last_clicked_at = timezone.now()
                snooper.ses_clicked_count += 1
                snooper.save()
                logger.info(f"CLICK: Processed Message-ID: {message_id}")
            except (AttributeError, PostOfficeEmail.DoesNotExist):
                logger.info(f"CLICK: No matching message found for :{message_id}")

        @receiver(bounce_received)
        def bounce_handler(sender, mail_obj, bounce_obj, raw_message, *args, **kwargs):
            """Handle SES incoming info"""

            message_id = _get_message_id(mail_obj)

            logger.info(f"BOUNCE: Received Message-ID: {message_id}")
            logger.error("Email Bounced")

            # print("\n\nmail obj", flush=True)
            # print(mail_obj, flush=True)
            #
            # print("\n\nbounce obj", flush=True)
            # print(bounce_obj, flush=True)

            message = f"Bounce received: bounce type: {bounce_obj['bounceType']}, bounce sub-type: {bounce_obj['bounceSubType']} bounced_recipients: {bounce_obj['bouncedRecipients']}"

            print(message, flush=True)

            log_event(
                user=None,
                severity="CRITICAL",
                source="Notifications",
                sub_source="Email",
                message=message,
            )

            # {'feedbackId': '0108017b6c09e065-31d447db-8629-4048-87a4-ce99d47eadc3-000000', 'bounceType': 'Permanent',
            #  'bounceSubType': 'General', 'bouncedRecipients': [
            #     {'emailAddress': 'bounce@simulator.amazonses.com', 'action': 'failed', 'status': '5.1.1',
            #      'diagnosticCode': 'smtp; 550 5.1.1 user unknown'}], 'timestamp': '2021-08-22T04:06:31.863Z',
            #  'reportingMTA': 'dns; b232-5.smtp-out.ap-southeast-2.amazonses.com'}

            try:
                post_office_email = PostOfficeEmail.objects.get(message_id=message_id)
                logger.error(f"ID: {post_office_email.id}")
            except (AttributeError, PostOfficeEmail.DoesNotExist):
                logger.info(f"BOUNCE: No matching message found for :{message_id}")

        @receiver(complaint_received)
        def complaint_handler(
            sender, mail_obj, complaint_obj, raw_message, *args, **kwargs
        ):
            """Handle SES incoming info"""

            message_id = _get_message_id(mail_obj)

            logger.info(f"COMPLAINT: Received Message-ID: {message_id}")
            logger.error("Email Complaint")

            try:
                post_office_email = PostOfficeEmail.objects.get(message_id=message_id)
                logger.error(f"ID: {post_office_email.id}")
            except (AttributeError, PostOfficeEmail.DoesNotExist):
                logger.info(f"COMPLAINT: No matching message found for :{message_id}")
