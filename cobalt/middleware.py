"""This middleware checks for the presence of an environment variable that puts the
site into maintenance mode. In maintenance mode normal users are shown a maintenance
screen, but admin users can still login and use the system as normal.

This must be added to the middleware variable in settings and must come after
"django.contrib.auth.middleware.AuthenticationMiddleware" as it needs access to
the authenticated user.
"""

from django.core.exceptions import MiddlewareNotUsed

import sys
import traceback as traceback_lib

from django.http import RawPostDataException
from django.shortcuts import render
from django.template.loader import render_to_string

from cobalt import settings
from utils.models import Error500


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        """This is called when the webserver starts. If we are not in maintenance mode then
        we can disable ourselves"""

        if settings.MAINTENANCE_MODE != "ON":
            raise MiddlewareNotUsed

        print(
            "\n\n*** Maintenance mode is on. Disable by changing environment variable MAINTENANCE_MODE ***"
        )
        print("*** Only superusers can access the system in maintenance mode. ***\n\n")

        # Maintenance mode is on - store get_response
        self.get_response = get_response

    def __call__(self, request):
        """This is called for every request if we are in maintenance mode"""

        response = self.get_response(request)

        # Allow superusers plus access to the login page and ses webhook (or it sends a million error emails)
        if request.user.is_superuser or request.META["PATH_INFO"] in [
            "/accounts/login/",
            "/notifications/ses/event-webhook/",
        ]:
            return response
        else:
            return render(request, "errors/503.html", status=503)


class CobaltLog500ErrorsMiddleware:
    """Middleware to record 500 errors on non-production environments"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):

        # Get the traceback info
        error_type, error_value, traceback = sys.exc_info()

        # Get further details of the traceback
        traceback_list = traceback_lib.format_exception(
            error_type, error_value, traceback
        )

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

        context = {
            "user": request.user,
            "error_type": f"{error_type}",
            "value_str": error_value,
            "traceback": traceback,
            "traceback_list": traceback_list,
            "request_post": request.POST,
            "request_get": request.GET,
            "request_path": request.path,
            "details": details,
            "headline_1": headline_1,
            "headline_2": headline_2,
        }

        # Turn into HTML
        email_body = render_to_string("errors/server_error_500.html", context)

        Error500(
            user=f"{request.user}"[:100],
            error=email_body,
            summary=error_value.__str__()[:200],
        ).save()
