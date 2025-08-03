import os
import sys

from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from cobalt.settings import COBALT_HOSTNAME
from tests.test_manager import CobaltTestManagerUnit


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Positional arguments

        parser.add_argument("--app", help="App name e.g. payments.")

    def handle(self, *args, **options):
        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        app = options["app"]

        # create testManager to oversee things
        manager = CobaltTestManagerUnit(app)
        manager.run()

        # file to store HTML output
        output_file = "/tmp/cobalt/unit-test-output.html"

        # make directory if not present
        os.makedirs(os.path.dirname(output_file))

        # write to file
        with open(output_file, "w") as html_file:
            html_file.write(manager.report_html())

        # notify user
        if manager.overall_success:
            print("All tests passed\n")
            print(f"Results are in {output_file}\n")
        else:
            # We have errors, so show output
            os.system("open /tmp/test-output.html")
