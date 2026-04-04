import datetime
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from events.models import Event, EventEntryPlayer, Session

_NOEMAIL = "noemail@notset.com"
_DEFAULT_DURATION = datetime.timedelta(hours=2)


def download_event_ics(request, event_id):
    """Download an ICS file containing one VEVENT per session for the given event.

    No login required — event data is public. Attendees are only included when
    the requesting user is authenticated and has an entry in this event.
    """

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

    # Collect co-players as attendees if the user is logged in and has an entry
    attendee_lines = []
    if request.user.is_authenticated:
        user_entry = (
            EventEntryPlayer.objects.select_related("event_entry")
            .filter(player=request.user, event_entry__event=event)
            .exclude(event_entry__entry_status="Cancelled")
            .first()
        )
        if user_entry:
            for ep in (
                EventEntryPlayer.objects.select_related("player")
                .filter(event_entry=user_entry.event_entry)
                .exclude(player=request.user)
            ):
                email = ep.player.email
                if email and email != _NOEMAIL:
                    attendee_lines.append(
                        f"ATTENDEE;CN={ep.player.full_name}:mailto:{email}"
                    )

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

        end_time = (
            session.session_end
            or (
                datetime.datetime.combine(session.session_date, session.session_start)
                + _DEFAULT_DURATION
            ).time()
        )
        dt_end = (
            session.session_date.strftime("%Y%m%d") + "T" + end_time.strftime("%H%M%S")
        )
        lines.append(f"DTEND;TZID=Australia/Sydney:{dt_end}")

        summary = f"{event.event_name} - Session {n}" if multi else event.event_name
        lines.append(f"SUMMARY:{summary}")

        if event.description:
            lines.append(f"DESCRIPTION:{event.description}")

        if location:
            lines.append(f"LOCATION:{location}")

        lines.extend(attendee_lines)
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    ics_content = "\r\n".join(lines) + "\r\n"

    response = HttpResponse(ics_content, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="event-{event_id}.ics"'
    return response


def _build_calendar_urls(event, sessions, guest_emails=None):
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

        end_time = (
            session.session_end
            or (
                datetime.datetime.combine(session.session_date, session.session_start)
                + _DEFAULT_DURATION
            ).time()
        )
        dt_end_google = (
            session.session_date.strftime("%Y%m%d") + "T" + end_time.strftime("%H%M%S")
        )
        dt_end_outlook = (
            session.session_date.strftime("%Y-%m-%d")
            + "T"
            + end_time.strftime("%H:%M:%S")
        )

        title = f"{event.event_name} - Session {n}" if multi else event.event_name

        google_params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{dt_start_google}/{dt_end_google}",
            "ctz": "Australia/Sydney",
        }
        if event.description:
            google_params["details"] = event.description
        if location:
            google_params["location"] = location
        if guest_emails:
            google_params["add"] = ",".join(guest_emails)

        google_url = (
            f"https://calendar.google.com/calendar/render?{urlencode(google_params)}"
        )

        outlook_params = {
            "subject": title,
            "startdt": dt_start_outlook,
            "enddt": dt_end_outlook,
        }
        if event.description:
            outlook_params["body"] = event.description
        if location:
            outlook_params["location"] = location
        if guest_emails:
            outlook_params["to"] = ";".join(guest_emails)

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
def calendar_buttons_htmx(request, event_id):
    """Return the calendar add-to-calendar buttons fragment for the given event.

    Only renders content for user pk=4 (dev test). Returns empty response for
    all other users so the hx-trigger="load" div on the events page is a no-op.
    """
    if request.user.pk != 4:
        return HttpResponse("")

    event = get_object_or_404(Event, pk=event_id)
    sessions = Session.objects.filter(event=event).order_by(
        "session_date", "session_start"
    )

    guest_emails = []
    user_entry = (
        EventEntryPlayer.objects.select_related("event_entry")
        .filter(player=request.user, event_entry__event=event)
        .exclude(event_entry__entry_status="Cancelled")
        .first()
    )
    if user_entry:
        for ep in (
            EventEntryPlayer.objects.select_related("player")
            .filter(event_entry=user_entry.event_entry)
            .exclude(player=request.user)
        ):
            email = ep.player.email
            if email and email != _NOEMAIL:
                guest_emails.append(email)

    calendar_sessions = _build_calendar_urls(event, sessions, guest_emails=guest_emails)

    ics_path = reverse("utils:download_event_ics", kwargs={"event_id": event.pk})
    ics_url = request.build_absolute_uri(ics_path)

    return render(
        request,
        "utils/_calendar_buttons_htmx.html",
        {
            "calendar_sessions": calendar_sessions,
            "ics_url": ics_url,
            "event_id": event_id,
        },
    )
