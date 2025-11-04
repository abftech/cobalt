import calendar
import html
import re
from datetime import datetime, date

import pytz
import requests
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect

from accounts.models import User, UnregisteredUser
from cobalt.settings import GLOBAL_MPSERVER, MP_USE_FILE, MP_USE_DJANGO, TIME_ZONE
from masterpoints.models import MPTran, Rank

TZ = pytz.timezone(TIME_ZONE)

def masterpoint_query_list(query):
    """Generic function to talk to the masterpoints SQL Server and return data as a list"""

    url = f"{GLOBAL_MPSERVER}/{query}"

    try:
        response = requests.get(url, timeout=10).json()
    except Exception as exc:
        print(exc)
        response = []

    return response


def masterpoint_query_row(query):
    """Generic function to get first row from query"""

    ret = masterpoint_query_list(query)
    if ret:
        return ret[0]
    return None


def mp_file_grep(pattern):
    with open("media/masterpoints/MPData.csv", "r", encoding="utf-8") as mp_file:
        for line in mp_file:
            if re.search(pattern, line):
                return line.split(",")


class MasterpointFactory:
    """Abstract class for accessing masterpoint data"""

    class Meta:
        abstract = True

    def get_masterpoints(self, system_number):
        """Get total masterpoints"""

    def system_number_lookup(self, system_number):
        """Look up the system number and return name"""

    def system_number_valid(self, system_number):
        """Look up the system number and return True if okay to add this user"""

    def user_summary(self, system_number):
        """Get basic information about a user"""


class MasterpointDB(MasterpointFactory):
    """Concrete implementation of a masterpoint factory using a database to get the data"""

    def get_masterpoints(self, system_number):
        """
        Retrieves the total masterpoints and rank for a given system number.

        Looks up the masterpoints database for the provided system number and returns a dictionary
        containing the total points and the rank name. If the system number is not found, returns
        'Not found' for both fields.

        Args:
            system_number: The unique identifier for the user in the masterpoints system.

        Returns:
            dict: A dictionary with keys 'points' and 'rank' representing the user's masterpoints and rank.
        """

        summary = masterpoint_query_row(f"mps/{system_number}")
        if summary:
            points = summary["TotalMPs"]
            rank = summary["RankName"] + " Master"
        else:
            points = "Not found"
            rank = "Not found"

        return {"points": points, "rank": rank}

    def system_number_lookup(self, system_number):
        result = masterpoint_query_row(f"id/{system_number}")
        if result:
            if User.objects.filter(
                system_number=system_number, is_active=True
            ).exists():
                return "Error: User already registered"
            if result["IsActive"] == "Y":
                # only use first name from given names
                given_name = result["GivenNames"].split(" ")[0]
                surname = result["Surname"]
                return html.unescape(f"{given_name} {surname}")

        return "Error: Invalid or inactive number"

    def system_number_valid(self, system_number):
        """Checks if this is valid, returns boolean. To be valid this must exist in the MPC with IsActive True
        and not already be a user in the system"""

        result = masterpoint_query_row(f"id/{system_number}")
        return bool(
            result
            and result["IsActive"] == "Y"
            and not User.objects.filter(
                system_number=system_number, is_active=True
            ).exists()
        )

    def system_number_lookup_api(self, system_number):
        """Called by the API"""
        result = masterpoint_query_row(f"id/{system_number}")
        if result:
            if User.objects.filter(
                system_number=system_number, is_active=True
            ).exists():
                return False, "User already registered"
            if result["IsActive"] == "Y":
                # only use first name from given names
                given_name = result["GivenNames"].split(" ")[0]
                surname = result["Surname"]
                return True, (given_name, surname)

        return False, "Invalid or inactive number"

    def user_summary(self, system_number):

        # Get summary data
        qry = f"{GLOBAL_MPSERVER}/mps/{system_number}"
        try:
            r = requests.get(qry).json()
        except (
            IndexError,
            requests.exceptions.InvalidSchema,
            requests.exceptions.MissingSchema,
            requests.exceptions.ConnectionError,
            requests.exceptions.JSONDecodeError,
            ConnectionError,
        ):
            r = []

        if not r:
            return None

        summary = r[0]

        # Set active to a boolean
        summary["IsActive"] = summary["IsActive"] == "Y"
        # Get home club name
        qry = f'{GLOBAL_MPSERVER}/club/{summary["HomeClubID"]}'
        summary["home_club"] = requests.get(qry).json()[0]["ClubName"]

        return summary

    def process_transactions(self, details, month, year):
        """
        Separate process and provisional details
        add formatting to the matchpoint numbers
        """
        provisional_details = []
        fixed_details = []
        month = int(month)
        year = int(year)
        for d in details:
            if d["PostingMonth"] >= month and d["PostingYear"] == year:
                provisional_details.append(d)
            else:
                fixed_details.append(d)
        return fixed_details, provisional_details

    def masterpoints_detail(self, request, system_number=None, years=1, retry=False):
        from masterpoints.views import masterpoint_query_local

        if system_number is None:
            system_number = request.user.system_number

        # Get summary data
        qry = "%s/mps/%s" % (GLOBAL_MPSERVER, system_number)
        r = masterpoint_query_local(qry)

        if len(r) == 0:

            if retry:  # This isn't the first time we've been here
                messages.error(
                    request,
                    f"Masterpoints module unable to find entry for id: {system_number}",
                    extra_tags="cobalt-message-error",
                )
                return False, None

            # not found - set error and call this again
            messages.warning(
                request,
                f"No Masterpoints entry found for id: {system_number}",
                extra_tags="cobalt-message-warning",
            )
            return self.masterpoints_detail(request, retry=True)

        summary = r[0]

        # Set active to a boolean
        if summary["IsActive"] == "Y":
            summary["IsActive"] = True
        else:
            summary["IsActive"] = False

        # Get provisional month and year, anything this date or later is provisional
        #   qry = "%s/provisionaldate" % GLOBAL_MPSERVER
        #   data = requests.get(qry).json()[0]
        #   prov_month = "%02d" % int(data["month"])
        #   prov_year = data["year"]

        # Get home club name
        qry = "%s/club/%s" % (GLOBAL_MPSERVER, summary["HomeClubID"])
        club = requests.get(qry).json()[0]["ClubName"]

        # Get last year in YYYY-MM format
        dt = date.today()
        dt = dt.replace(year=dt.year - years)
        year = dt.strftime("%Y")
        month = dt.strftime("%m")

        # Get the detail list of recent activity
        qry = "%s/mpdetail/%s/postingyear/%s/postingmonth/%s" % (
            GLOBAL_MPSERVER,
            system_number,
            year,
            month,
        )
        details = requests.get(qry).json()

        counter = summary["TotalMPs"]  # we need to construct the balance to show
        gold = float(summary["TotalGold"])
        red = float(summary["TotalRed"])
        green = float(summary["TotalGreen"])

        # build list for the fancy chart at the top while we loop through.
        labels_key = []
        labels = []
        chart_green = {}
        chart_red = {}
        chart_gold = {}

        # build chart labels
        # go back a year then move forward
        rolling_date = datetime.today() + relativedelta(years=-years)

        for i in range(12 * years + 1):
            year = rolling_date.strftime("%Y")
            month = rolling_date.strftime("%m")
            labels_key.append("%s-%s" % (year, month))
            if years == 1:
                labels.append(rolling_date.strftime("%b"))
            else:
                labels.append(rolling_date.strftime("%b %Y"))
            rolling_date = rolling_date + relativedelta(months=+1)
            chart_gold["%s-%s" % (year, month)] = 0.0
            chart_red["%s-%s" % (year, month)] = 0.0
            chart_green["%s-%s" % (year, month)] = 0.0

        details, futureTrans = self.process_transactions(details, month, year)
        # todo: Tanmay to first extract details into two--> one current month next -- "future"
        # deatils will just have till current month future will go in provisional variable
        # loop through the details and augment the data to pass to the template
        # we are just adding running total data for the table of details
        for d in details:
            counter = counter - d["mps"]

            d["running_total"] = counter
            d["PostingDate"] = "%s-%02d" % (d["PostingYear"], d["PostingMonth"])
            d["PostingDateDisplay"] = "%s-%s" % (
                calendar.month_abbr[d["PostingMonth"]],
                d["PostingYear"],
            )

            # Its too slow to filter at the db so skip any month we don't want
            if not d["PostingDate"] in chart_gold:
                continue

            if d["MPColour"] == "Y":
                gold = gold - float(d["mps"])
                chart_gold[d["PostingDate"]] = chart_gold[d["PostingDate"]] + float(
                    d["mps"]
                )
            elif d["MPColour"] == "R":
                red = red - float(d["mps"])
                chart_red[d["PostingDate"]] = chart_red[d["PostingDate"]] + float(d["mps"])
            elif d["MPColour"] == "G":
                green = green - float(d["mps"])
                chart_green[d["PostingDate"]] = chart_green[d["PostingDate"]] + float(
                    d["mps"]
                )

        # fill in the chart data
        running_gold = float(summary["TotalGold"])
        gold_series = []
        for label in reversed(labels_key):
            running_gold = running_gold - chart_gold[label]
            gold_series.append(float("%.2f" % running_gold))
        gold_series.reverse()

        running_red = float(summary["TotalRed"])
        red_series = []
        for label in reversed(labels_key):
            running_red = running_red - chart_red[label]
            red_series.append(float("%.2f" % running_red))
        red_series.reverse()

        running_green = float(summary["TotalGreen"])
        green_series = []
        for label in reversed(labels_key):
            running_green = running_green - chart_green[label]
            green_series.append(float("%.2f" % running_green))
        green_series.reverse()

        chart = {
            "labels": labels,
            "gold": gold_series,
            "red": red_series,
            "green": green_series,
        }

        total = "%.2f" % (green + red + gold)
        green = "%.2f" % green
        red = "%.2f" % red
        gold = "%.2f" % gold

        bottom = {"gold": gold, "red": red, "green": green, "total": total}

        # Show bullets on lines or not
        if years > 2:
            show_point = "false"
        else:
            show_point = "true"

        # Show title every X points
        points_dict = {1: 1, 2: 3, 3: 5, 4: 12, 5: 12}
        try:
            points_every = points_dict[years]
        except KeyError:
            points_every = len(labels) - 1  # start and end only

        timescale = f"Last {years} years"

        if years == 1:
            timescale = "Last 12 Months"

        return True, {
                "details": details,
                "summary": summary,
                "club": club,
                "chart": chart,
                "bottom": bottom,
                "show_point": show_point,
                "points_every": points_every,
                "system_number": system_number,
                "timescale": timescale,
            }



class MasterpointDjango(MasterpointFactory):
    """Concrete implementation of a masterpoint factory using local tables in Django to get the data"""

    def _get_masterpoints_by_colour(self, system_number):
        """ returns the total masterpoints for a user, broken down by colour """

        # Get Green, Red and Gold masterpoints for this system_number
        total_mps = MPTran.objects.filter(system_number=system_number).values("mp_colour").order_by("mp_colour").annotate(total=Sum("mp_amount"))

        green = 0
        red = 0
        gold = 0

        for item in total_mps:
            if item["mp_colour"] == "G":
                green = item["total"]
            elif item["mp_colour"] == "R":
                red = item["total"]
            if item["mp_colour"] == "Y":
                gold = item["total"]

        return green + red + gold, green, red, gold

    def get_masterpoints(self, system_number):
        """
        Retrieves the total masterpoints and rank for a given system number.

        Does this using local tables.

        Args:
            system_number: The unique identifier for the user in the masterpoints system.

        Returns:
            dict: A dictionary with keys 'points' and 'rank' representing the user's masterpoints and rank.
        """

        # Get Green, Red and Gold masterpoints for this system_number
        total, green, red, gold = self._get_masterpoints_by_colour(system_number)

        # Get rank
        rank = Rank.objects.filter(total_needed__lte=total, gold_needed__lte=gold, red_gold_needed__lte=red+gold).last()

        print("Using Django for Masterpoints")

        return {"points": total, "rank": f"{rank} Master"}

    def system_number_lookup(self, system_number):
        """ Used for registering new users through the web sign up form """

        if User.objects.filter(system_number=system_number, is_active=True):
            return "Error: User already registered"

        unregistered = UnregisteredUser.objects.filter(system_number=system_number).first()
        if unregistered and unregistered.is_active:
            given_name = unregistered.first_name.split(" ")[0]
            surname = unregistered.last_name
            return html.unescape(f"{given_name} {surname}")

        return "Error: Invalid or inactive number"

    def system_number_valid(self, system_number):
        """Checks if this is valid, returns boolean. To be valid this must exist in the MPC with IsActive True
        and not already be a user in the system"""

        # See if user exists
        if User.objects.filter(system_number=system_number).exists():
            return False

        # ee if unregistered user exists
        user = UnregisteredUser.objects.filter(system_number=system_number).first()

        if not user or not user.is_active:
            return False

        return True

    def system_number_lookup_api(self, system_number):
        """Called by the API"""

        if User.objects.filter(
                system_number=system_number, is_active=True
        ).exists():
            return False, "User already registered"

        user = UnregisteredUser.objects.filter(system_number=system_number).first()

        if not user or not user.is_active:
            return False, "Invalid or inactive number"

        given_name = user.first_name.split(" ")[0]
        surname = user.last_name
        return True, (given_name, surname)

    def user_summary(self, system_number):
        """ Basic Masterpoint related information about a user

            Returns e.g.:
                {
                'ABFNumber': '620246',
                'Surname': 'Guthrie',
                'GivenNames': 'Mark',
                'IsActive': True,
                'TotalMPs': 1028.22,
                'TotalGold': 451.25, '
                TotalRed': 483.01, '
                TotalGreen': 93.96,
                'RankName': 'Grand',
                'home_club': 'North Shore Bridge Club Inc'
                }

        """
        user = User.objects.filter(system_number=system_number).first() or UnregisteredUser.objects.filter(system_number=system_number).first()

        if not user:
            return None

        # Get Green, Red and Gold masterpoints for this system_number
        total, green, red, gold = self._get_masterpoints_by_colour(system_number)

        rank = Rank.objects.filter(total_needed__lte=total, gold_needed__lte=gold,
                                   red_gold_needed__lte=red + gold).last()

        return {
            'ABFNumber': system_number,
            'Surname': user.last_name,
            'GivenNames': user.first_name,
            'HomeClubID': 74,
            'IsActive': user.is_active,
            'TotalMPs': total,
            'TotalGold': gold,
            'TotalRed': red,
            'TotalGreen': green,
            'RankName': rank.rank_name,
            'home_club': 'Home Club is Hardcoded',
        }

    def masterpoints_detail(self, request, system_number=None, years=1):

        # Use logged in user if nothing specified
        if not system_number:
            system_number = request.user.system_number

        # Get summary data
        summary = self.user_summary(system_number)
        if not summary:
            messages.error(
                request,
                f"Masterpoints module unable to find entry for id: {system_number}",
                extra_tags="cobalt-message-error",
            )
            return False, None

        # Get the details
        start_date = datetime.now(tz=TZ) - relativedelta(years=years)
        details = MPTran.objects.filter(system_number=system_number).filter(mp_batch__posted_date__gte=start_date).order_by("-mp_batch__posted_date")

        counter = summary["TotalMPs"]  # we need to construct the balance to show
        gold = float(summary["TotalGold"])
        red = float(summary["TotalRed"])
        green = float(summary["TotalGreen"])

        # build list for the fancy chart at the top while we loop through.
        labels_key = []
        labels = []
        chart_green = {}
        chart_red = {}
        chart_gold = {}

        # build chart labels
        # go back a year then move forward
        rolling_date = datetime.now(tz=TZ) + relativedelta(years=-years)

        for _ in range(12 * years + 1):
            year = rolling_date.strftime("%Y")
            month = rolling_date.strftime("%m")
            labels_key.append(f"{year}-{month}")
            if years == 1:
                labels.append(rolling_date.strftime("%b"))
            else:
                labels.append(rolling_date.strftime("%b %Y"))
            rolling_date = rolling_date + relativedelta(months=+1)
            chart_gold[f"{year}-{month}"] = 0.0
            chart_red[f"{year}-{month}"] = 0.0
            chart_green[f"{year}-{month}"] = 0.0

        # loop through the details and augment the data to pass to the template
        # we are just adding running total data for the table of details
        for item in details:
            counter = counter - item.mp_amount

            item.running_total = counter

            # Its too slow to filter at the db so skip any month we don't want
            # if not item["PostingDate"] in chart_gold:
            #     continue

            year_month = item.mp_batch.posted_date.strftime("%Y-%m")

            if item.mp_colour == "Y":
                gold = gold - float(item.mp_amount)
                chart_gold[year_month] = chart_gold[year_month] + float(item.mp_amount)
            elif item.mp_colour == "R":
                red = red - float(item.mp_amount)
                chart_red[year_month] = chart_red[year_month] + float(item.mp_amount)
            elif item.mp_colour == "G":
                green = green - float(item.mp_amount)
                chart_green[year_month] = chart_green[year_month] + float(item.mp_amount)

        # fill in the chart data
        running_gold = float(summary["TotalGold"])
        gold_series = []
        for label in reversed(labels_key):
            running_gold = running_gold - chart_gold[label]
            gold_series.append(float("%.2f" % running_gold))
        gold_series.reverse()

        running_red = float(summary["TotalRed"])
        red_series = []
        for label in reversed(labels_key):
            running_red = running_red - chart_red[label]
            red_series.append(float("%.2f" % running_red))
        red_series.reverse()

        running_green = float(summary["TotalGreen"])
        green_series = []
        for label in reversed(labels_key):
            running_green = running_green - chart_green[label]
            green_series.append(float("%.2f" % running_green))
        green_series.reverse()

        chart = {
            "labels": labels,
            "gold": gold_series,
            "red": red_series,
            "green": green_series,
        }

        total = "%.2f" % (green + red + gold)
        green = "%.2f" % green
        red = "%.2f" % red
        gold = "%.2f" % gold

        bottom = {"gold": gold, "red": red, "green": green, "total": total}

        # Show bullets on lines or not
        show_point = "false" if years > 2 else "true"

        # Show title every X points
        points_dict = {1: 1, 2: 3, 3: 5, 4: 12, 5: 12}
        try:
            points_every = points_dict[years]
        except KeyError:
            points_every = len(labels) - 1  # start and end only

        timescale = f"Last {years} years"

        if years == 1:
            timescale = "Last 12 Months"

        return True, {
                "details": details,
                "summary": summary,
                "club": summary["home_club"],
                "chart": chart,
                "bottom": bottom,
                "show_point": show_point,
                "points_every": points_every,
                "system_number": system_number,
                "timescale": timescale,
            }

class MasterpointFile(MasterpointFactory):
    """Concrete implementation of a masterpoint factory using a file to get the data"""

    def get_masterpoints(self, system_number):

        pattern = f"{int(system_number):07}"
        result = mp_file_grep(pattern)

        if result:
            points = result[7]
            rank = f"{result[19]} Master"
        else:
            points = "Not found"
            rank = "Not found"

        return {"points": points, "rank": rank}

    def system_number_lookup(self, system_number):

        pattern = f"{int(system_number):07}"
        result = mp_file_grep(pattern)

        if result:
            if User.objects.filter(
                system_number=system_number, is_active=True
            ).exists():
                return "Error: User already registered"
            if result[6] == "Y":
                # only use first name from given names
                given_name = result[2].split(" ")[0]
                surname = result[1]
                return html.unescape(f"{given_name} {surname}")

        return "Error: Inactive or invalid number"

    def system_number_valid(self, system_number):
        """Checks if this is valid, returns boolean. To be valid this must exist in the MPC with IsActive True
        and not already be a user in the system"""

        pattern = f"{int(system_number):07}"
        result = mp_file_grep(pattern)

        return bool(
            result
            and result[6] == "Y"
            and not User.objects.filter(
                system_number=system_number, is_active=True
            ).exists()
        )

    def user_summary(self, system_number):

        pattern = f"{int(system_number):07}"
        result = mp_file_grep(pattern)

        if not result:
            return None

        return {
            "GivenNames": result[2],
            "Surname": result[1],
            "IsActive": result[6],
            "home_club": None,
        }


def masterpoint_factory_creator():
    print(f"{MP_USE_DJANGO=}")
    if MP_USE_FILE:
        return MasterpointFile()
    elif MP_USE_DJANGO:
        return MasterpointDjango()
    else:
        return MasterpointDB()
