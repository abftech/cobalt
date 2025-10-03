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
    # You should be able to use: timezone.make_aware(midnight_datetime, TZ)
    # But it will give you a time 5 minutes later than you want by getting the timezone wrong
    # Instead of 00:00:00+10 you get 00:00:00+10:05
    # So we use TZ.localize() which gets it right
    return TZ.localize(midnight_datetime)


def start_end_date_to_datetime(start_date: str, end_date: str):
    """helper to convert start and end date to date times

    dates should be strings in the format "YYYY-MM-DD" e.g. "2045-11-03"

    """

    # Convert dates to date times
    start_datetime_raw = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    start_datetime = TZ.localize(start_datetime_raw)

    # Start date is 00:00 time on the day, for end date use 00:00 time on the next day
    end_datetime_raw = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    end_datetime_raw += datetime.timedelta(days=1)
    end_datetime = TZ.localize(end_datetime_raw)

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
