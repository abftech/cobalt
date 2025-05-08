import os
import sys

from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from cobalt.settings import COBALT_HOSTNAME
from tests.test_manager import CobaltTestManagerIntegration


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Positional arguments

        parser.add_argument("--app", help="App name e.g. payments.")
        parser.add_argument("--browser", help="Browser - default is chrome")
        parser.add_argument(
            "--base_url", help="Base url for server e.g. http://127.0.0.1:8088"
        )
        parser.add_argument(
            "--headless", help="Specify an value to run browser in the background"
        )
        parser.add_argument(
            "--single_test",
            help="Class name of a test to only run one test and not them all",
        )

    def handle(self, *args, **options):

        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        app = options["app"]
        browser = options["browser"]
        base_url = options["base_url"]
        headless = options["headless"]
        single_test = options["single_test"]

        # create testManager to oversee things
        manager = CobaltTestManagerIntegration(
            app, browser, base_url, headless, single_test
        )
        manager.run()
        #        if not manager.overall_success:
        with open("/tmp/test-output.html", "w") as html_file:
            html_file.write(manager.report_html())
        os.system("utils/cgit/tools/open_report.sh")
