from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def release_notes_view(request):
    """show the release notes"""

    release_notes = [
        {
            "release": "6.1.1",
            "notes": [
                "Fix sort order on Helpdesk views",
                "Add release notes",
                "Improved server error 500 handling",
                "Documentation for email",
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
