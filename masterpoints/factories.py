import html
import re

import requests

from accounts.models import User
from cobalt.settings import GLOBAL_MPSERVER, MP_USE_FILE


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
    return MasterpointFile() if MP_USE_FILE else MasterpointDB()
