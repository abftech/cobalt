import html
import re

import requests
from django.db.models import Sum

from accounts.models import User, UnregisteredUser
from cobalt.settings import GLOBAL_MPSERVER, MP_USE_FILE, MP_USE_DJANGO
from masterpoints.models import MPTran, Rank


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
