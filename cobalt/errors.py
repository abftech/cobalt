import sys
import traceback as traceback_lib

from django.http import RawPostDataException, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from cobalt import settings
from cobalt.settings import SERVER_EMAIL
from notifications.views.core import send_cobalt_email_with_template
from utils.models import Error500


def not_found_404(request, exception=None):
    return render(request, "errors/404.html", {}, status=404)


def permission_denied_403(request, exception):
    return render(request, "errors/500.html")


def bad_request_400(request, exception):
    return render(request, "errors/500.html")


def server_error_500(request):
    """
    Email the admins when a 500 error occurs
    """

    # Get the traceback info
    error_type, error_value, traceback = sys.exc_info()

    # Get further details of the traceback
    traceback_list = traceback_lib.format_exception(error_type, error_value, traceback)

    try:
        headline_1 = traceback_list[-2]
    except IndexError:
        headline_1 = "Not available"

    try:
        headline_2 = traceback_list[-1]
    except IndexError:
        headline_2 = "Not available"

    # Try to get the details
    try:
        details = f"BODY: {request.body}"
    except RawPostDataException:
        details = "BODY: UNAVAILABLE"

    # Block post data for logins - has password details
    if request.path == "/accounts/login":
        request_post = "NOT LOGGED"
        details = "NOT LOGGED"
    else:
        request_post = request.POST

    # Django post office can't store objects, so we need to render the body of the email first
    context = {
        "user": request.user,
        "error_type": f"{error_type}",
        "value_str": error_value,
        "traceback": traceback,
        "traceback_list": traceback_list,
        "request_post": request_post,
        "request_get": request.GET,
        "request_path": request.path,
        "details": details,
        "headline_1": headline_1,
        "headline_2": headline_2,
    }

    # Turn into HTML
    email_body = render_to_string("errors/server_error_500.html", context)

    # django post office doesn't like new lines in subject
    error_value = f"{error_value}".replace("\n", "").replace("\r", "")

    # Get addresses to send to
    to_emails = []
    for recipient in settings.ADMINS:
        to_emails.append(recipient[1])

    # send email
    po_context = {
        "title": f"Server Error - {error_value}",
        "email_body": email_body,
    }

    send_cobalt_email_with_template(
        to_emails,
        po_context,
        template="system - server error",
        sender=SERVER_EMAIL,
    )

    # Log it
    Error500(user=request.user[:10], error=email_body, summary=error_value[:200]).save()

    # Don't return status of 500 or it will trigger Django's own email sending
    if request.user.is_authenticated:
        return render(request, "errors/500.html")
    else:
        return render(request, "errors/logged_out_error_500.html")


def generate_error_500(request):
    """force a 500 error to test handling"""

    print(1 / 0)
