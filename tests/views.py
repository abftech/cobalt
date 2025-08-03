"""We needed to do some testing on the htmx search and it seemed useful to add a test url for it"""

from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.timezone import now


@login_required()
def htmx_search(request):
    return render(request, "tests/search/htmx_search.html")


@login_required()
def button_test(request):
    """Test hyperscript button reveal problem"""
    return render(request, "tests/button_test.html")


def create_smoke_test_report():
    """The smoke tests are called from a shell script which creates a
    file with the outcomes. This is called from a management command
    to use that file to create a report similar to the unit and integration
    test reports.
    """

    # File is of format:
    #
    # start time
    # 01_test_something 0
    # 02_test_something_else 1
    #
    # 0 = success
    # 1 = failure

    with open("/tmp/smoke_test_outcome.txt") as smoke_results:
        raw_results = smoke_results.readlines()

    # first line is start time of tests
    start_time = datetime.fromtimestamp(int(raw_results[0]), timezone.utc)

    # Convert to dictionary with name of test and boolean for success or failure
    results = {}
    for line in raw_results[1:]:
        items = line.strip().split(" ")

        # remove extension e.g. 01_test_something.txt -> 01_test_something
        test_name = items[0].split(".")[0]

        results[test_name] = items[1] == "0"

    # Work out total score
    passed = 0
    for test_item in results:
        if results[test_item]:
            passed += 1

    score = passed / len(results)

    if score == 1.0:
        total_score = "A+"
    elif score > 0.95:
        total_score = "A-"
    elif score > 0.9:
        total_score = "B+"
    elif score > 0.85:
        total_score = "B-"
    elif score > 0.8:
        total_score = "C+"
    elif score > 0.7:
        total_score = "C-"
    elif score > 0.6:
        total_score = "D-"
    else:
        total_score = "Fail"

    data = {
        "results": results,
        "start_time": start_time,
        "elapse": now() - start_time,
        "document_title": "Smoke Test Report",
        "total_score": total_score,
        "icon": "build",
        "total_passing": passed,
        "total_length": len(results),
    }

    report_html = render_to_string("tests/smoke_test_results.html", data)

    with open("/tmp/test-output.html", "w", encoding="utf-8") as html_file:
        html_file.write(report_html)
