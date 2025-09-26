import csv
import datetime
from time import sleep

import dateutil.utils
import requests
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import make_aware, get_current_timezone
from geopy import Nominatim

from api.models import ApiLog
from rbac.decorators import rbac_check_role
from utils.utils import cobalt_paginator


@login_required()
def geo_location(request, location):
    """return lat and long for a text address"""

    try:
        geolocator = Nominatim(user_agent="cobalt")
        loc = geolocator.geocode(location)
        html = {"lat": loc.latitude, "lon": loc.longitude}
        data_dict = {"data": html}
        return JsonResponse(data=data_dict, safe=False)
    except:  # noqa E722
        return JsonResponse({"data": {"lat": None, "lon": None}}, safe=False)


def download_csv(self, request, queryset):
    """Copied from Stack Overflow - generic CSV download"""

    model = queryset.model
    model_fields = model._meta.fields + model._meta.many_to_many
    field_names = [field.name for field in model_fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="export.csv"'

    # the csv writer
    writer = csv.writer(response)
    # Write a first row with header information
    writer.writerow(field_names)
    # Write data rows
    for row in queryset:
        values = []
        for field in field_names:
            value = getattr(row, field)

            values.append(value)
        writer.writerow(values)

    return response


def masterpoint_query(query):
    """Generic function to talk to the masterpoints server and return data

    Takes in a SQLServer query e.g. "select count(*) from table"

    Returns an iterable, either an empty list or the response from the server.

    In case there is a problem connecting to the server, this will do everything it
    can to fail silently.

    """

    # Try to load data from MP Server

    try:
        response = requests.get(query, timeout=10).json()
    except Exception as exc:
        print(exc)
        response = []

    return response


@rbac_check_role("system.admin.edit")
def api_log_viewer(request):
    """Allow admins to see calls to the API"""

    # Get all records
    api_logs = ApiLog.objects.order_by("-pk")
    things = cobalt_paginator(request, api_logs)

    # Get summary
    three_months_ago = timezone.now() - relativedelta(months=3)
    summary = (
        ApiLog.objects.filter(created_date__gte=three_months_ago)
        .values("api", "version")
        .annotate(total=Count("api"))
        .order_by("-total")
    )
    print(summary)

    return render(
        request, "utils/api_log_viewer.html", {"things": things, "summary": summary}
    )


def timeout(request):
    """simulate a timeout for testing purposes"""

    sleep(100)

    return HttpResponse("time out test")


def cobalt_report_ref_dates(request: HttpRequest = None):
    """
    Common function to handle dates

    Accepts an optional HttpRequest which can contain POST data with a "ref_date" parameter
    ref_date should be dd/mm/yyyy

    Used for when you want to get things like the first and last date of the previous month

    Returns a dictionary of timezone aware dates, can be updated if anything is missing

        ref_date: last day of previous month, or ref_date value from request
        ref_date_month_earlier: date a month earlier, same day of month

    """

    # Get date from request if provided
    start_date = request.POST.get("ref_date") if request else None

    if start_date:
        ref_date = datetime.datetime.strptime(start_date, "%d/%m/%Y")
        ref_date = ref_date.replace(hour=23, minute=59, second=59, microsecond=999_999)
    else:
        # Default to last day of previous month
        today = datetime.date.today()
        first = today.replace(day=1)
        last_day_of_last_month = first - datetime.timedelta(days=1)
        ref_date = datetime.datetime(
            year=last_day_of_last_month.year,
            month=last_day_of_last_month.month,
            day=last_day_of_last_month.day,
            hour=23,
            minute=59,
            second=59,
            microsecond=999_999,
        )

    # Make timezone aware
    ref_date = make_aware(ref_date, get_current_timezone())

    # Also calculate date a month earlier
    ref_date_month_earlier = ref_date - relativedelta(months=1)

    # return dictionary of dates
    return {"ref_date": ref_date, "ref_date_month_earlier": ref_date_month_earlier}
