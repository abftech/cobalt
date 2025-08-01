from datetime import timedelta

from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import strip_tags

from accounts.models import User
from cobalt.settings import DEFAULT_FROM_EMAIL, SUPPORT_EMAIL
from events.models import EventLog
from organisations.models import ClubLog
from utils.utils import cobalt_paginator
from .models import Log


def get_client_ip(request):
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    else:
        return request.META.get("REMOTE_ADDR")


def log_event(user, severity, source, sub_source, message, request=None):
    """Event Logging. Main function.

    Note: user parameter can be string or a User object

    Args:
        user(User or str): who was involved
        severity: how bad
        source: where did it come from
        sub_source: next level where did it come from
        message: text
        request:

    Logging needs to be very defensive, we don't want logging to cause an outage (happened once already)

    """

    # If we got a real user then use that for the user_object, and use the text name for the user
    if isinstance(user, User):
        user_object = user
        user = user.full_name
    else:
        user_object = None

    # User may not be a string or have a __str__ function
    try:
        user = user[:200]
    except (KeyError, TypeError):
        user = "Unknown"

    # Validate
    if severity:
        severity = severity[:8]
    if source:
        source = source[:30]
    if sub_source:
        sub_source = sub_source[:50]

    # See if we can get the IP address
    try:
        ip = get_client_ip(request)[:15] if request else None
    except (TypeError, AttributeError):
        ip = None

    # Create entry
    Log(
        user=user,
        user_object=user_object,
        ip=ip,
        severity=severity,
        source=source,
        sub_source=sub_source,
        message=message,
    ).save()

    if severity == "CRITICAL":

        try:
            mail_subject = f"{severity} - {source}"
            message = (
                "Severity: %s\nSource: %s\nSub-Source: %s\nUser: %s\nMessage: %s"
                % (
                    severity,
                    source,
                    sub_source,
                    user,
                    message,
                )
            )
            send_mail(
                mail_subject,
                message,
                DEFAULT_FROM_EMAIL,
                SUPPORT_EMAIL,
                fail_silently=False,
            )
        except Exception as e:
            print(f"{e}")


@user_passes_test(lambda u: u.is_superuser)
def home(request):
    form_severity = request.GET.get("severity")
    form_source = request.GET.get("source")
    form_sub_source = request.GET.get("sub_source")
    form_days = request.GET.get("days")
    form_user = request.GET.get("user")

    days = int(form_days) if form_days else 7

    ref_date = timezone.now() - timedelta(days=days)

    events_list = Log.objects.filter(event_date__gte=ref_date).select_related(
        "user_object"
    )

    # only show sub sources if sources has been selected
    sub_sources = None

    if form_severity not in ["All", None]:
        events_list = events_list.filter(severity=form_severity)

    if form_user not in ["All", None]:
        events_list = events_list.filter(user__contains=form_user)

    if form_source not in ["All", None]:
        events_list = events_list.filter(source=form_source)
        sub_sources = events_list.values("sub_source").distinct()

        if form_sub_source not in ["All", None]:
            events_list = events_list.filter(sub_source=form_sub_source)

    # lists should be based upon other filters
    severities = events_list.values("severity").distinct()
    sources = events_list.values("source").distinct()
    users = events_list.exclude(user=None).values("user").distinct()

    unique_users = []
    for user in users:
        this_user = strip_tags(user["user"])
        if this_user not in unique_users:
            unique_users.append(this_user)

    unique_users.sort()

    return render(
        request,
        "logs/event_list.html",
        {
            "things": events_list,
            "severities": severities,
            "days": days,
            "form_severity": form_severity,
            "sources": sources,
            "form_source": form_source,
            "form_sub_source": form_sub_source,
            "sub_sources": sub_sources,
            "form_user": form_user,
            "users": unique_users,
        },
    )


def get_logs_statistics():
    """return basic stats on logs. Called by utils statistics"""

    total_logs = Log.objects.count()
    total_critical_logs = Log.objects.filter(
        severity=Log.SeverityCodes.CRITICAL
    ).count()
    event_logs = EventLog.objects.count()
    club_logs = ClubLog.objects.count()

    return {
        "total_logs": total_logs,
        "total_critical_logs": total_critical_logs,
        "event_logs": event_logs,
        "club_logs": club_logs,
    }
