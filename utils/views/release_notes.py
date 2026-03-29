from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from events.models import Event, Session


@login_required
def download_event_ics(request, event_id):
    """Download an ICS file containing one VEVENT per session for the given event."""

    event = Event.objects.select_related("congress").get(pk=event_id)
    sessions = Session.objects.filter(event=event).order_by(
        "session_date", "session_start"
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ABF//MyABF//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    venue_parts = []
    if event.congress.venue_name:
        venue_parts.append(event.congress.venue_name)
    if event.congress.venue_location:
        venue_parts.append(event.congress.venue_location)
    location = ", ".join(venue_parts)

    session_list = list(sessions)
    multi = len(session_list) > 1

    for n, session in enumerate(session_list, start=1):
        dt_start = (
            session.session_date.strftime("%Y%m%d")
            + "T"
            + session.session_start.strftime("%H%M%S")
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:cobalt-event-{event_id}-session-{session.pk}@myabf.com.au",
            f"DTSTART;TZID=Australia/Sydney:{dt_start}",
        ]

        if session.session_end:
            dt_end = (
                session.session_date.strftime("%Y%m%d")
                + "T"
                + session.session_end.strftime("%H%M%S")
            )
            lines.append(f"DTEND;TZID=Australia/Sydney:{dt_end}")

        summary = f"{event.event_name} - Session {n}" if multi else event.event_name
        lines.append(f"SUMMARY:{summary}")

        if event.description:
            lines.append(f"DESCRIPTION:{event.description}")

        if location:
            lines.append(f"LOCATION:{location}")

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    ics_content = "\r\n".join(lines) + "\r\n"

    response = HttpResponse(ics_content, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="event-{event_id}.ics"'
    return response


def _build_calendar_urls(event, sessions):
    """Return a list of dicts with Google and Outlook calendar URLs, one per session."""

    venue_parts = []
    if event.congress.venue_name:
        venue_parts.append(event.congress.venue_name)
    if event.congress.venue_location:
        venue_parts.append(event.congress.venue_location)
    location = ", ".join(venue_parts)

    calendar_sessions = []
    session_list = list(sessions)
    multi = len(session_list) > 1

    for n, session in enumerate(session_list, start=1):
        label_date = session.session_date.strftime("%a %-d %b")
        label_time = session.session_start.strftime("%-I:%M%p").lower()
        label = (
            f"Session {n} \u2014 {label_date} {label_time}"
            if multi
            else f"{label_date} {label_time}"
        )

        dt_start_google = (
            session.session_date.strftime("%Y%m%d")
            + "T"
            + session.session_start.strftime("%H%M%S")
        )
        dt_start_outlook = (
            session.session_date.strftime("%Y-%m-%d")
            + "T"
            + session.session_start.strftime("%H:%M:%S")
        )

        if session.session_end:
            dt_end_google = (
                session.session_date.strftime("%Y%m%d")
                + "T"
                + session.session_end.strftime("%H%M%S")
            )
            dt_end_outlook = (
                session.session_date.strftime("%Y-%m-%d")
                + "T"
                + session.session_end.strftime("%H:%M:%S")
            )
        else:
            dt_end_google = dt_start_google
            dt_end_outlook = dt_start_outlook

        google_params = {
            "action": "TEMPLATE",
            "text": f"{event.event_name} - Session {n}",
            "dates": f"{dt_start_google}/{dt_end_google}",
        }
        if event.description:
            google_params["details"] = event.description
        if location:
            google_params["location"] = location

        google_url = (
            f"https://calendar.google.com/calendar/render?{urlencode(google_params)}"
        )

        outlook_params = {
            "subject": f"{event.event_name} - Session {n}",
            "startdt": dt_start_outlook,
            "enddt": dt_end_outlook,
        }
        if event.description:
            outlook_params["body"] = event.description
        if location:
            outlook_params["location"] = location

        outlook_url = f"https://outlook.live.com/calendar/0/deeplink/compose?{urlencode(outlook_params)}"
        office365_url = f"https://outlook.office.com/calendar/0/deeplink/compose?{urlencode(outlook_params)}"

        calendar_sessions.append(
            {
                "label": label,
                "google_url": google_url,
                "outlook_url": outlook_url,
                "office365_url": office365_url,
            }
        )

    return calendar_sessions


@login_required
def release_notes_view(request):
    """show the release notes"""

    # To get a list of differences between this branch and develop you can run:
    #
    #  git log develop..HEAD --no-merges --format="%ad %s" --date=short

    release_notes = [
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

    event = Event.objects.select_related("congress").filter(pk=553).first()
    calendar_sessions = []
    ics_url = None

    if event:
        sessions = Session.objects.filter(event=event).order_by(
            "session_date", "session_start"
        )
        calendar_sessions = _build_calendar_urls(event, sessions)
        ics_url = reverse("utils:download_event_ics", kwargs={"event_id": 5536})

    return render(
        request,
        "utils/release_notes_view.html",
        {
            "release_notes": release_notes,
            "event": event,
            "calendar_sessions": calendar_sessions,
            "ics_url": ics_url,
        },
    )
