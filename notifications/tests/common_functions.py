import logging

from post_office.models import Email

from tests.test_manager import CobaltTestManagerIntegration

logger = logging.getLogger("cobalt")


def check_email_sent(
    manager: CobaltTestManagerIntegration = None,
    test_name: str = "",
    test_description: str = "",
    email_to: str = None,
    subject_search: str = None,
    body_search: str = None,
    email_count: int = 10,
    debug: bool = False,
    save_results: bool = True,
):
    """
    Check if an email has been sent. This isn't the greatest test going around. Email addresses get changed
    by the playpen checks and you can also find older emails that match by accident. Emails really need to
    be manually tested as you need to look at the presentation as well as the content, but this is better
    than nothing.

    NOTE: This is used by both integration tests and smoke tests

    Search parameters will combine, e.g. if you provide email_to and subject_search
    then both need to match for this to succeed.

    Args:
        manager: standard manager object (only needed if save_results=True)
        test_name: Name for this test to appear in report (only needed if save_results=True)
        test_description: Description for this test (only needed if save_results=True)
        subject_search: string to search for in the email subject
        body_search: string to search for in the email body
        email_to: first name of person sent the email. Assumes using normal templates for this.
        email_count: how many recent emails to look through
        debug: print diagnostics
        save_results: flag to save results (for integration tests) or not (for smoke tests)
    """

    try:
        last_email = Email.objects.order_by("-pk")[0].pk
    except (AttributeError, IndexError):
        error_message = "Email Check: No emails found at all - emails are empty"
        if debug:
            logger.critical(error_message)
        if save_results:
            manager.save_results(
                status=False,
                output=error_message,
                test_name=test_name,
                test_description=test_description,
            )
        return False, error_message

    # We can't use the ORM to filter emails, we need to call Django Post Office functions
    emails = Email.objects.filter(id__gt=last_email - email_count)

    ok, output = _check_email_sent_tests(
        email_count,
        email_to,
        emails,
        subject_search,
        body_search,
        debug,
    )

    output += f" Result was '{ok}'"

    if save_results:
        manager.save_results(
            status=ok,
            output=output,
            test_name=test_name,
            test_description=test_description,
        )

    return ok, output


def _check_email_sent_tests_list_emails(debug, emails):
    """sub of _check_email_sent_tests. Lists emails if debug is set"""

    if debug:
        mail_count = Email.objects.count()
        logger.debug(f"There are {mail_count} emails. Email list follows")
        for email in emails:
            logger.debug(
                f"To: {email.context['name']}   Subject: {email.context['title']}"
            )


def _check_email_sent_tests_handle_email_to(output, email_to, emails, debug):
    """sub of _check_email_sent_tests"""

    if debug:
        logger.debug(f"Checking {emails.count()} emails.")

    ok = False
    output += f"Looking for to={email_to}. "

    for email in emails:
        try:
            if email.context["name"] == email_to:
                ok = True
                _debug_mail_print(email, debug, "email_to", email_to)
            else:
                emails = emails.exclude(pk=email.id)
        except TypeError:
            if debug:
                logger.debug(
                    "Email Check: TypeError exception in checking email_to. email.context['name'] not found."
                )

        # Remove email if no match
        if not ok:
            emails = emails = emails.exclude(pk=email.id)

    if debug:
        logger.debug(
            f"Finished handle_email_to. There are now {emails.count()} emails."
        )

    return ok, output, emails


def _check_email_sent_tests_handle_subject(output, subject_search, debug, emails):
    """sub of _check_email_sent_tests to handle subject searches"""

    if debug:
        logger.debug(f"Checking {emails.count()} emails.")

    ok = False

    output += f"looking for '{subject_search}' in subject. "
    for email in emails:
        try:
            if email.context["subject"].find(subject_search) >= 0:
                ok = True
                _debug_mail_print(email, debug, "subject", subject_search)
        except TypeError:
            if debug:
                print(
                    "Email Check: TypeError exception in checking subject_search. email.context['name'] not found."
                )

        # Remove email if no match
        if not ok:
            emails = emails.exclude(pk=email.id)

    if debug:
        logger.debug(
            f"Finished handle_email_to. There are now {emails.count()} emails."
        )

    return ok, output, emails


def _check_email_sent_tests_handle_body(output, body_search, debug, emails):
    """sub of _check_email_sent_tests to handle searching the email body"""

    if debug:
        logger.debug(f"Checking {emails.count()} emails.")

    ok = False

    output += f"body contains '{body_search}' "
    for email in emails:
        try:
            if email.context["email_body"].find(body_search) >= 0:
                ok = True
                _debug_mail_print(email, debug, "body", "body too long for debug")

        except TypeError:
            if debug:
                logger.debug(
                    "Email Check: TypeError exception in checking body_search. email.context['name'] not found."
                )

        # Remove email if no match
        if not ok:
            emails = emails.exclude(pk=email.id)

    if debug:
        logger.debug(f"Finished handle_body. There are now {emails.count()} emails.")

    return ok, output, emails


def _check_email_sent_tests(
    email_count, email_to, emails, subject_search, body_search, debug=False
):
    """Sub step of check_email_sent. Does the actual checking."""

    ok = False

    if not emails:
        return False, "No emails found at all. Could not search."

    _check_email_sent_tests_list_emails(debug, emails)

    # Output string has a story to tell
    output = f"Looked through last {email_count} emails for an email matching search criteria. "

    if email_to:

        ok, output, emails = _check_email_sent_tests_handle_email_to(
            output, email_to, emails, debug
        )

        if not ok:
            output += "Failed on email_to."
            if debug:
                logger.debug(
                    "Email Check: Failed to match any emails in email_to check"
                )
            return ok, output

    if subject_search:

        ok, output, emails = _check_email_sent_tests_handle_subject(
            output, subject_search, debug, emails
        )

        if not ok:
            output += "Failed on subject_search."
            if debug:
                logger.debug(
                    "Email Check: Failed to match any emails in subject_search check"
                )
            return ok, output

    if body_search:

        ok, output, emails = _check_email_sent_tests_handle_body(
            output, body_search, debug, emails
        )

        if not ok:
            output += "Failed on body_search."
            if debug:
                logger.debug(
                    "Email Check: Failed to match any emails in body_search check"
                )
            return ok, output

    output += f"Matched on {emails.count()} emails. Emails were {emails}"

    return ok, output


def _debug_mail_print(email, debug, check, search_str):
    """helper to print debug info for email searches"""

    if not debug:
        return

    logger.debug(
        f"debug: {check}: looked for '{search_str}'. Match: id: {email.id} to: {email.context['name']} subject: {email.context['subject']}"
    )
