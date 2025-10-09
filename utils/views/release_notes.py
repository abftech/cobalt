from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def release_notes_view(request):
    """show the release notes"""

    release_notes = [
        {
            "release": "6.1.9",
            "notes": [
                "DEV - Increase email_count for event entry tests",
                "Extend global search to include Unregistered users and contacts",
                "Add global admin ability to remove AWS email blocks for unregistered users and contacts",
                "Add club admin ability to remove AWS email blocks for unregistered users and contacts",
                "Add link to member email to user profile",
                "DEV - Minor changes to test harness",
                "More accurate error if viewing an unpublished congress",
                "Fix bug where entry is left in cart if congress is auto closed",
                "Fix Django admin view of MemberMembershipType",
                "Update accounts documentation to include club memberships and contacts",
                "Fix bug on entry fees for member only events",
                "DEV - Update cgit_dev_rebuild_local_db to close active connections",
                "DEV - Improve stripe API checks for development",
                "Add event id to cancelled event entries",
                "Prevent editing of old congresses",
                "Additional finance reports",
                "Handle congress having no payment methods",
                "DEV - update copy to local db",
                "DEV - minor changes to cgit scripts",
                "Fix organisations view in Django admin",
                "Fix viewing of events without sessions",
                "Fix Stripe previous month transactions download",
                "Fix dates on other Stripe reports",
                "Remove warning message on Stripe reports when changing dates",
                "DEV - Add list filters to some Django admin views",
                "Prevent deletion of last session in a published event",
                "Check events are in the same congress before allowing a entry to be moved",
            ],
        },
        {
            "release": "6.1.8",
            "notes": [
                "Fix reply_to bug after Django update",
            ],
        },
        {
            "release": "6.1.7",
            "notes": [
                "Added results_url to congresses",
                "Global search pagination issue",
                "System settings updates - update environment names",
            ],
        },
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
