from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def release_notes_view(request):
    """show the release notes"""

    release_notes = [
        {
            "release": "6.1.6",
            "notes": [
                "Many changes to smoke test harness",
                "Small bug fixes - 1027, 1011",
            ],
        },
        {
            "release": "6.1.5",
            "notes": [
                "Added script to check code versions",
                "Fixed test data for memberships",
                "Added tests for membership self payment",
                "Fixed double payment bug for memberships",
                "Changed database reload scripts to include membership data",
            ],
        },
        {
            "release": "6.1.4",
            "notes": [
                "Update email priority for error emails",
            ],
        },
        {
            "release": "6.1.3",
            "notes": [
                "Update email address for error emails",
            ],
        },
        {
            "release": "6.1.2",
            "notes": [
                "Update email address for error emails",
                "Log 500 errors in a table",
            ],
        },
        {
            "release": "6.1.1",
            "notes": [
                "Fix sort order on Helpdesk views",
                "Add release notes",
                "Improved server error 500 handling",
                "Documentation for email",
                "Better handling for Masterpoint server being unavailable",
                "Minor cgit script changes",
            ],
        },
        {
            "release": "6.1.0",
            "notes": [
                "Upgrade to Python 3.13",
                "Upgrade to Django 5.2",
                "Many package upgrades",
            ],
        },
    ]

    return render(
        request,
        "utils/release_notes_view.html",
        {
            "release_notes": release_notes,
        },
    )
