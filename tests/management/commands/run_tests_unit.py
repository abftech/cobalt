import os
import sys

from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from cobalt.settings import COBALT_HOSTNAME
from tests.test_manager import CobaltTestManagerUnit


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--app", help="App name e.g. payments.")

    def handle(self, *args, **options):
        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        app = options["app"]

        manager = CobaltTestManagerUnit(app)
        manager.run()

        output_file = "/tmp/cobalt/unit-test-output.html"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as html_file:
            html_file.write(manager.report_html())

        if manager.overall_success:
            print("All tests passed\n")
            print(f"Results are in {output_file}\n")
        else:
            os.system(f"open {output_file}")
            sys.exit(1)
