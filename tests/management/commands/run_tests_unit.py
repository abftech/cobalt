import glob
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from cobalt.settings import BASE_DIR, COBALT_HOSTNAME
from tests.test_manager import CobaltTestManagerUnit


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--app", help="App name e.g. payments.")
        parser.add_argument(
            "--workers",
            type=int,
            default=1,
            help="Number of parallel workers (unit tests only).",
        )
        parser.add_argument(
            "--no-open",
            action="store_true",
            help="Suppress opening the HTML report in a browser (used by parallel subprocesses).",
        )

    def handle(self, *args, **options):
        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        app = options["app"]
        workers = options["workers"]
        no_open = options["no_open"]

        if workers > 1 and not app:
            success = self._run_parallel(workers)
            if not success:
                sys.exit(1)
            return

        manager = CobaltTestManagerUnit(app)
        manager.run()

        # Per-app output file when --app is set (avoids collisions in parallel mode)
        suffix = f"-{app}" if app else ""
        output_file = f"/tmp/cobalt/unit-test-output{suffix}.html"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as html_file:
            html_file.write(manager.report_html())

        if manager.overall_success:
            print("All tests passed\n")
            print(f"Results are in {output_file}\n")
        else:
            if not no_open:
                os.system(f"open {output_file}")
            sys.exit(1)

    def _run_parallel(self, workers):
        apps = sorted(
            {test_file.split("/")[0] for test_file in glob.glob("*/tests/unit/*.py")}
        )

        manage_py = os.path.join(BASE_DIR, "manage.py")

        def run_app(app):
            cmd = [
                sys.executable,
                manage_py,
                "run_tests_unit",
                "--app",
                app,
                "--no-open",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return app, result

        overall_success = True
        print(
            f"Running unit tests for {len(apps)} apps with up to {workers} workers...\n"
        )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(run_app, app): app for app in apps}
            for future in as_completed(futures):
                app, result = future.result()
                passed = result.returncode == 0
                if not passed:
                    overall_success = False
                status = "PASS" if passed else "FAIL"
                print(f"[{status}] {app}")
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr)

        print("\n-----------------------------------------")
        if overall_success:
            print("All apps passed.")
        else:
            print("Some apps FAILED. See output above.")
        print("-----------------------------------------\n")

        return overall_success
