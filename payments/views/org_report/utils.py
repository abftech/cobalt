import datetime

import pytz
from django.utils import timezone, dateformat

from cobalt.settings import TIME_ZONE

TZ = pytz.timezone(TIME_ZONE)


def format_date_helper(input_date):
    """format a date"""

    local_dt = timezone.localtime(input_date, TZ)
    return dateformat.format(local_dt, "Y-m-d H:i:s")


def date_to_datetime_midnight(input_date):
    """turn a date into a datetime with a time of midnight"""
    midnight_datetime = datetime.datetime.combine(
        input_date, datetime.datetime.min.time()
    )
    return timezone.make_aware(midnight_datetime, TZ)


def start_end_date_to_datetime(start_date, end_date):
    """helper to convert start and end date to date times"""

    # Convert dates to date times
    start_datetime_raw = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    start_datetime = timezone.make_aware(start_datetime_raw, TZ)

    # Start date is 00:00 time on the day, for end date use 00:00 time on the next day
    end_datetime_raw = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    end_datetime_raw += datetime.timedelta(days=1)
    end_datetime = timezone.make_aware(end_datetime_raw, TZ)

    return start_datetime, end_datetime


def derive_counterparty(organisation_transaction):
    """get the counterparty from an OrganisationTransaction object"""

    # counterparty
    if organisation_transaction.member:
        return organisation_transaction.member.__str__()
    elif organisation_transaction.other_organisation:
        return organisation_transaction.other_organisation.__str__()
    else:
        return ""
