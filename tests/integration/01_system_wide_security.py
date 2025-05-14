import re
import subprocess
from time import sleep

import requests

from tests.test_manager import CobaltTestManagerIntegration

# URLs that do not require authentication
NON_AUTH_URLS = [
    "/accounts/loggedout",
    "/accounts/login/",
    "/accounts/activate/dummy/dummy/",
    "/accounts/password-reset-request",
    "/accounts/password_reset/",
    "/accounts/password_reset/done/",
    "/accounts/register/1/dummy",
    "/accounts/register",
    "/accounts/reset/<uidb64>/<token>/",
    "/accounts/reset/done/",
    "/accounts/signin",
    "/accounts/test_email_send",
    "/admin/login/",
    "/dashboard/help",
    "/dashboard/logged-out",
    "/events/",
    "/events/congress-listing/dummy",
    "/events/congress/get_all_congresses",
    "/events/congress/view/1",
    "/events/congress/view/1/1",
    "/events/congress/event/view-event-entries/1/1",
    "/organisations/public-profile/1",
    "/summernote/upload_attachment/",
    "/support/acceptable-use",
    "/support/contact",
    "/support/contact-logged-out",
    "/support/cookies",
    "/support/guidelines",
    "/support/acceptable-use-logged-out",
    "/support/cookies-logged-out",
    "/view",
    "/summernote/editor/<id>/",  # TODO: Double check this one
    "/api/cobalt/keycheck/v1.0",
    "/api/cobalt/system-number-lookup/v1.0",
    "/api/docs/",
    "/api/openapi.json",
    "/accounts/unregistered-preferences/dummy",
    "/masterpoints/abf-registration-card",
    "/masterpoints/abf-registration-card-htmx",
    "/404",
    "/500",
]

# URLs that we do not test
DO_NOT_TEST_URLS = [
    "/masterpoints/system_number_lookup",
    "/accounts/create-pdf-system-card/",
    "/xero/",
    "/xero/callback",
    "/xero/config",
    "/xero/initialise",
    "/xero/refresh",
    "/xero/run-xero-api",
    "/payments/statement-org-summary",
]


class TestURLsRequireLogin:
    """Tests all available URLs require the user to be authenticated unless specifically
    not required.

    """

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.client = self.manager.client

    def a1_test_all_urls(self):
        """It is easiest to use manage.py show_urls to get the URLs. We filter out
        the Django admin commands as we don't need to test Django here"""

        # Health should probably be removed altogether from Cobalt
        # We don't test API as they are mostly Posts
        process = subprocess.Popen(
            [
                r"./manage.py show_urls | awk '{print $1}' | grep -v '^\/admin' | grep -v '^\/health' | grep -v '^\/api'"
            ],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        urls = []
        # Go through the list of URLs and format them to work
        for line in process.stdout.readlines():
            url = line.decode("utf-8").strip()
            if url in DO_NOT_TEST_URLS:
                continue
            # If we have a parameter, then change it to a value
            # ? makes the expression not greedy so it can handle multiple parameters
            url = re.sub("<int(.*?)>", "1", url)
            url = re.sub("<str(.*?)>", "dummy", url)

            urls.append(url)

        # Start with empty list of errors
        errors = []

        # Go through URLs and test them
        for url in urls:

            if url in NON_AUTH_URLS:
                continue

            # get response. We expect to get 302 - redirect to login page, but 40x are okay too
            response = requests.get(f"{self.manager.base_url}{url}")

            print(response.status_code, response.url)

            if not (
                # We are okay if we get a redirect or not found code
                response.status_code in {302, 400, 403, 404, 405}
                # or if the url is the login page (since upgrade to Django 5)
                or response.url.find("/accounts/login/") != -1
                # or if the url is the logged out page
                or response.url.find("http://127.0.0.1:8088/view") != -1
            ):
                errors.append(f"{url} - {response.status_code}")

        self.manager.save_results(
            status=not errors,
            test_name="Check URLs require authentication",
            test_description="We go through all URLs (except Django Admin) and check that we cannot access "
            "them if not logged in. We allow a specific set of exceptions. ",
            output=f"URLs found: {len(urls)}. URLs ignored {len(DO_NOT_TEST_URLS)}. "
            f"URLs expected to allow unauthorised access {len(NON_AUTH_URLS)}. "
            f"Errors {errors}",
        )
