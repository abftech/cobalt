from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from tests.simple_selenium_parser import simple_selenium_parser, command_lookup

# This import is required. Used in an exec()
from tests.simple_selenium import SimpleSelenium

ALLOWED_PRODUCTION_SCRIPTS = ["basic_smoke_test_production.txt"]


def list_commands_helper():
    """list out the help for the commands by using the doc strings of the function calls"""

    print("\nKeyword                        Purpose")
    print("=======                        =======\n")

    for item in command_lookup:

        start_point = command_lookup[item].find(".") + 1
        end_point = command_lookup[item].find("(")
        method_name = command_lookup[item][start_point:end_point]
        cmd = f"print('{item: <30}', SimpleSelenium.{method_name}.__doc__)"
        exec(cmd)

    print("\n")


class Command(BaseCommand):
    def add_arguments(self, parser):

        parser.add_argument(
            "--list",
            action="store_true",
            help="List commands available for use in scripts",
        )
        parser.add_argument(
            "--password", help="password for user. Leave blank for default."
        )
        parser.add_argument("--userid", help="user to run the test under")
        parser.add_argument(
            "--silent", action="store_true", help="don't display any output"
        )
        parser.add_argument("--script", help="script to execute")
        parser.add_argument("--browser", help="Browser - default is chrome")
        parser.add_argument(
            "--base_url", help="Base url for server e.g. http://127.0.0.1:8088"
        )
        parser.add_argument(
            "--show",
            action="store_true",
            help="Specify to run browser in the foreground",
        )

    def handle(self, *args, **options):

        show = options["show"]
        browser = options["browser"]
        base_url = options["base_url"]
        password = options["password"]
        userid = options["userid"]
        script = options["script"]
        silent = options["silent"]
        list_commands = options["list"]

        # Be protective of production
        if (
            base_url in ["https://myabf.com.au", "https://www.myabf.com.au"]
            and script not in ALLOWED_PRODUCTION_SCRIPTS
        ):
            raise SuspiciousOperation(
                "This script is not permitted to be run against production"
            )

        if list_commands:
            return list_commands_helper()

        if not base_url:
            base_url = "https://test.myabf.com.au"

        if not password:
            password = "F1shcake"

        simple_selenium_parser(
            script,
            base_url=base_url,
            userid=userid,
            show=show,
            browser=browser,
            silent=silent,
            password=password,
        )
