"""

Daily task to inform conveners about congresses which have finished and there are unpaid entries,
also fixes congresses if they qualify.

"""

import datetime
import logging

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.urls import reverse

from accounts.models import User
from cobalt.settings import ABF_USER
from events.views.core import (
    get_completed_congresses_with_money_due,
    fix_closed_congress,
)

# Set thresholds
from notifications.views.core import send_cobalt_email_with_template
from utils.models import BatchStatus

logger = logging.getLogger("cobalt")

FIRST_WARNING_DAYS = 2
AUTO_FIX_UNLESS_OVERRIDDEN_DAYS = 7
AUTO_FIX_REGARDLESS_MONTHS = 3


def send_first_warning(congress):
    """send the first warning to the convener"""

    print("Sending first warning for", congress)

    email_body = f"""
                    <h1>Completed Congress with Outstanding Payments</h1>
                    <p>You are registered as the contact email for <b>{congress}</b> on MyABF that finished
                    {FIRST_WARNING_DAYS} days ago.</p>
                    <p>This congress still has outstanding payments due.<p>
                    <p>You have three options:<p>
                    <ol>
                    <li>Do nothing and we will automatically close off the payments in
                    {AUTO_FIX_UNLESS_OVERRIDDEN_DAYS - FIRST_WARNING_DAYS} days.
                    <li>Click on the link below to edit the congress and correct payments now.
                    <li>Click on the link below to prevent automatic closure of this congress to give you
                    more time to sort out the missing payments.
                    <ul>
    """

    context = {
        "name": "Tournament Organiser",
        "title": f"Congress Requiring Attention - {congress}",
        "email_body": email_body,
        "box_colour": "#007bff",
        "link": reverse("events:admin_summary", kwargs={"congress_id": congress.id}),
        "link_text": "View Congress",
    }

    send_cobalt_email_with_template(
        to_address=congress.contact_email,
        context=context,
    )


def send_last_warning(congress):
    """send the last warning to the convener"""

    if congress.do_not_auto_close_congress:
        print(f"{congress} is set to not auto close")
        return

    print(f"Sending last warning for {congress}")

    email_body = f"""
                     <h1>Completed Congress with Outstanding Payments - Final Notice</h1>
                     <p>You are registered as the contact email for <b>{congress}</b> on MyABF that finished
                     {FIRST_WARNING_DAYS} days ago.</p>
                     <p>This congress still has outstanding payments due.<p>
                     <p>You have three options:<p>
                     <ol>
                     <li>Do nothing and we will automatically close off the payments in
                     {AUTO_FIX_UNLESS_OVERRIDDEN_DAYS} days.
                     <li>Click on the link below to edit the congress and correct payments now.
                     <li>Click on the link below to prevent automatic closure of this congress to give you
                     more time to sort out the missing payments.
                     <ul>
     """

    context = {
        "name": "Tournament Organiser",
        "title": f"Congress Requiring Attention - Final Notice - {congress}",
        "email_body": email_body,
        "box_colour": "#007bff",
        "link": reverse("events:admin_summary", kwargs={"congress_id": congress.id}),
        "link_text": "View Congress",
    }

    send_cobalt_email_with_template(
        to_address=congress.contact_email,
        context=context,
    )


def fix_congress_normal(congress, system_account):
    """fix congress on normal date"""

    print("Fixing congress after normal delay", congress)

    results = fix_closed_congress(congress, system_account)

    email_body = f"""
                     <h1>Completed Congress with Outstanding Payments - Closed</h1>
                     <p>You are registered as the contact email address for <b>{congress}</b> on MyABF that finished
                     on {congress.end_date:%-d %B %Y}.</p>
                     <p>This congress still had outstanding payments due.<p>
                     <p>We have adjusted all outstanding amounts to regard them as paid and marked them as
                     “System adjusted”  This removes any debts still showing to players.</p>
                     <h2>There is nothing more to do</h2>
                     <br>
                     {results}
     """

    context = {
        "name": "Tournament Organiser",
        "title": f"Congress Issues Resolved - {congress}",
        "email_body": email_body,
        "box_colour": "#007bff",
        "link": reverse("events:admin_summary", kwargs={"congress_id": congress.id}),
        "link_text": "View Congress",
    }

    send_cobalt_email_with_template(
        to_address=congress.contact_email,
        context=context,
    )


def fix_congress_after_extension(congress, system_account):
    """fix congress anyway after 3 months"""

    print("Fixing congress after 3 months", congress)

    results = fix_closed_congress(congress, system_account)

    email_body = f"""
                     <h1>Completed Congress with Outstanding Payments - Closed After {AUTO_FIX_REGARDLESS_MONTHS} months</h1>
                     <p>You are registered as the contact email for <b>{congress}</b> on MyABF that finished
                     on {congress.end_date:%-d %B %Y}.</p>
                     <p>This congress still had outstanding payments due.<p>
                     <p>We have adjusted all outstanding amounts to regard them as paid and marked them as
                     “System adjusted”  This removes any debts still showing to players.</p>
                     <h2>There is nothing more to do</h2>
                     <br>
                     {results}
     """

    context = {
        "name": "Tournament Organiser",
        "title": f"Congress Issues Resolved - {congress}",
        "email_body": email_body,
        "box_colour": "#007bff",
        "link": reverse("events:admin_summary", kwargs={"congress_id": congress.id}),
        "link_text": "View Congress",
    }

    send_cobalt_email_with_template(
        to_address=congress.contact_email,
        context=context,
    )


class Command(BaseCommand):
    def handle(self, *args, **options):

        logger.info("Handling closed congresses with problems...")

        batch = BatchStatus.objects.create(
            command="handle_closed_congresses_with_unpaid_entries"
        )
        summary_lines = []

        try:
            congresses = get_completed_congresses_with_money_due()

            logger.info(f"Found {len(congresses)} congress(es) to investigate")
            summary_lines.append(
                f"Found {len(congresses)} congress(es) with outstanding payments."
            )

            system_account = User.objects.get(pk=ABF_USER)

            first_warnings = 0
            last_warnings = 0
            normal_fixes = 0
            extended_fixes = 0

            # Go through congresses
            for congress in congresses:

                # Check if just come up for follow up
                if datetime.date.today() == congress.end_date + relativedelta(
                    days=FIRST_WARNING_DAYS
                ):
                    send_first_warning(congress)
                    first_warnings += 1

                # Check if just about to be automatically fixed
                elif datetime.date.today() == congress.end_date + relativedelta(
                    days=AUTO_FIX_UNLESS_OVERRIDDEN_DAYS - 1
                ):
                    send_last_warning(congress)
                    if not congress.do_not_auto_close_congress:
                        last_warnings += 1

                # Auto close
                elif (
                    datetime.date.today()
                    >= congress.end_date
                    + relativedelta(days=AUTO_FIX_UNLESS_OVERRIDDEN_DAYS)
                    and not congress.do_not_auto_close_congress
                ):
                    fix_congress_normal(congress, system_account)
                    normal_fixes += 1

                # Final closure regardless
                # COB-776: Fixed to test for correct time delta
                elif (
                    datetime.date.today()
                    >= congress.end_date
                    + relativedelta(months=AUTO_FIX_REGARDLESS_MONTHS)
                    and congress.do_not_auto_close_congress
                ):
                    fix_congress_after_extension(congress, system_account)
                    extended_fixes += 1

            summary_lines.append(f"First warnings sent: {first_warnings}")
            summary_lines.append(f"Last warnings sent: {last_warnings}")
            summary_lines.append(f"Auto-fixed (normal): {normal_fixes}")
            summary_lines.append(f"Auto-fixed (after extension): {extended_fixes}")

        except Exception as e:
            logger.exception(
                "handle_closed_congresses_with_unpaid_entries failed with an unhandled exception"
            )
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("handle_closed_congresses_with_unpaid_entries finished")
