from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def release_notes_view(request):
    """show the release notes"""

    # To get a list of differences between this branch and develop you can run:
    #
    #  git log develop..HEAD --no-merges --format="%ad %s" --date=short

    release_notes = [
        {
            "release": "6.3.13",
            "date": "14th April 2026",
            "notes": [
                "DEV - Add date to release",
            ],
        },
        {
            "release": "6.3.12",
            "notes": [
                "DEV - Test harness changes to run in parallel",
            ],
        },
        {
            "release": "6.3.11",
            "notes": [
                "DEV - Fix 500 error when opening extras panel for visitor session entries",
                "DEV - Fix 500 error when sending welcome pack to new MPC member",
                "DEV - Fix 500 error viewing results with single traveller line per board",
                "DEV - Fix 500 error in congress finance report for deleted events",
                "DEV - Fix 500 error uploading USEBIO pairs results missing PERCENTAGE/PLACE",
                "DEV - Fix 500 error when congress entry answer exceeds field length; add validation",
                "DEV - Fix 500 error on Stripe pending admin page for customers with no setup intents",
                "DEV - Fix 500 error in manual adjustment CSV export when settlement amount is null",
            ],
        },
        {
            "release": "6.3.10",
            "notes": [
                "Fix for email call using old parameters",
            ],
        },
        {
            "release": "6.3.9",
            "notes": [
                "Snooper model change to match production for potential rollback",
            ],
        },
        {
            "release": "6.3.8",
            "notes": [
                "DEV - Notification model problem",
                "Fix opening Snooper records through Django Admin",
            ],
        },
        {
            "release": "6.3.7",
            "notes": [
                "Fix N+1 issue with email viewer",
                "Xero set up instructions",
                "Prevent double click for processing bridge credits in club session",
                "Fix extra logo in some email clients",
                "Notification view - use correct field names",
                "Remove old code for email batch size",
                "DEV - bug in _cgit_test_handle_db script",
            ],
        },
        {
            "release": "6.3.6",
            "notes": [
                "Stripe API security fix",
            ],
        },
        {
            "release": "6.3.5",
            "notes": [
                "Fix dashboard to allow viewing discussions on a smaller screen",
                "Django 5.2.12",
                "DEV - CGIT changes",
                "DEV - Add to calendar currently hidden",
            ],
        },
        {
            "release": "6.3.4",
            "notes": [
                "Logging for batch jobs",
                "Email preview bug",
                "Double dummy solver",
                "Cross IMPs support for results",
                "Results - support Butler movements",
                "Results - better handling of unsupported event types",
                "Restrict uploads for results to be XML only",
                "Xero API",
                "Settlement changed to use Xero",
                "Bug fix for auto_pay_batch to handle unknown ABF number",
                "Fix errors in off-system backups",
                "Add index to post office email table",
                "DEV - script to clear locks",
                "DEV - archive old data script - not complete",
                "Improve performance of ABF finance screen",
                "DEV - Improve performance of API for sending results",
            ],
        },
        {
            "release": "6.3.3",
            "notes": [
                "Warn before syncing data from MPC if there is existing data",
                "Additional warning when turning on full club management",
                "Handle spam for Helpdesk module",
                "Change some uses of Due Date in memberships to Lapse Date for clarity",
                "Logging for off system backups",
                "Ability to run ./manage.py commands from web browser",
                "Ability to edit active memberships",
                "Add counter to event summary admin screen",
                "Default auto-pay date to 7 days",
            ],
        },
        {
            "release": "6.3.2",
            "notes": [
                "Add table lock to payment updates to prevent incorrect balance problems",
                "Return to deleting FCM devices if errors are found when sending messages",
                "Fix for adding tagged contacts to emails",
            ],
        },
        {
            "release": "6.3.1",
            "notes": [
                "DEV - Merge release 6.2.x into 6.3.x",
            ],
        },
        {
            "release": "6.3.0",
            "notes": [
                "Remove use of UnregisteredUsers ahead of Masterpoints work",
            ],
        },
        {
            "release": "6.2.6",
            "notes": [
                "Fix for Django admin search for congress master",
                "Handle no rbac group found for old congress master screen",
                "Fix edit sessions view for events",
                "Fix bug in adding member if renewal date = today",
                "Club reporting for deleted events",
            ],
        },
        {
            "release": "6.2.5",
            "notes": [
                "Fix for results view MASTER_POINTS_AWARDED issue",
            ],
        },
        {
            "release": "6.2.4",
            "notes": [
                "Congress admin - update event_id on payment records if entry is moved",
                "DEV - Upgrade Python packages",
                "DEV - Faster way to get Production data into a development environment",
                "Calendar - allow multiple selections",
                "Viewer for 500 errors and middleware to capture if debug is on",
                "Fixes for club admin finance breakdown report",
            ],
        },
        {
            "release": "6.2.3",
            "notes": [
                "Club admin pay anyone - prevent both congress and membership fee flags together",
                "Changes to club movement report",
                "Fix bug with results not handling voids for Double Dummy Solver",
                "DEV - update sanitise data script for testing to include FCMDevices",
                "DEV - Cobalt tags handle missing values better",
                "New sub report for movement report showing session payments by date",
                "Fix for COB-1073, error when creating blank session",
            ],
        },
        {
            "release": "6.2.2",
            "notes": [
                "Documentation for mobile app",
                "Add index to payments abstract class for session_id",
                "Bug fix for new congresses after changing form in 6.1.9",
            ],
        },
        {
            "release": "6.2.1",
            "notes": [
                "Update new relic package",
            ],
        },
        {
            "release": "6.2.0",
            "notes": [
                "Comment out club movement report",
            ],
        },
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
                "Extend admin organisation movement report to provide breakdowns",
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
        {"release_notes": release_notes},
    )
