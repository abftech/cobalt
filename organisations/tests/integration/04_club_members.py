import datetime
import time
from datetime import timedelta

from django.utils.timezone import now

from organisations.models import Organisation, MemberMembershipType
from organisations.tests.integration.common_functions import (
    club_menu_go_to_tab,
    login_and_go_to_club_menu,
)
from tests.integration.common_functions import cobalt_htmx_user_search
from tests.test_manager import CobaltTestManagerIntegration

# TODO: See if these constants can be centrally stored

# State id numbers
NSW = 3
QLD = 5

# Org org_id numbers
CANBERRA_ID = 1851
TRUMPS_ID = 2259
SUNSHINE_ID = 4680
WAVERLEY_ID = 3480

# Org names
club_names = {
    CANBERRA_ID: "Canberra Bridge Club Inc",  # ACT
    TRUMPS_ID: "Trumps Bridge Centre",  # NSW
    SUNSHINE_ID: "Sunshine Coast Contract Bridge Club Inc",  # QLD
    WAVERLEY_ID: "Waverley Bridge Club",  # VIC
}


def _csv_upload_helper(
    manager,
    system_number,
    first_name,
    last_name,
    bridge_club,
    test_name,
    expect_to_fail=False,
):
    """helper to upload a CSV and check it works. Only processes one row. Must already be on the upload page"""

    # Create CSV
    with open("/tmp/members.csv", "w") as csv:
        csv.write(
            "ABF Number, First Name, Last Name, Email, Membership Type, Address 1, Address 2, State, Postcode, Preferred Phone, Other Phone, Date of Birth, Club Membership Number, Joined Date, Left Date, Emergency Contact, Notes, Membership Start Date, Membership End Date\n"
        )

        membership_start_date = now().date().strftime("%d/%m/%Y")
        membership_end_date = datetime.date(year=now().year + 1, month=1, day=1)
        csv.write(
            f"{system_number}, {first_name}, {last_name}, email@madeup.com,Standard, 1 High St, Low Country, NSW, 2000,,,,,2000-01-01,,Harry Potter,These are notes,{membership_start_date},{membership_end_date}\n"
        )

    # Import from CSV
    # Click Add
    manager.selenium_wait_for("t_member_tab_add").click()
    # Click MPC Import
    manager.selenium_wait_for("t_csv_upload").click()
    # find file button
    file_button = manager.selenium_wait_for("file-upload")

    file_button.send_keys("/tmp/members.csv")

    # click the submit button
    manager.selenium_wait_for("upload_pianola").click()

    # Wait
    manager.selenium_find_text_on_page("Import Complete")

    # Check membership was created
    membership = MemberMembershipType.objects.filter(
        membership_type__organisation=bridge_club, system_number=system_number
    ).first()

    status = bool(membership)

    if expect_to_fail:
        status = not status

    manager.save_results(
        status=status,
        test_name=f"Member CSV Upload - {test_name}",
        test_description=f"Import {first_name} {last_name} - {system_number}. {expect_to_fail=}",
    )

    manager.sleep()


class ClubMembers:
    """Tests for club menu members. Some of these tests connect to the MPC so data may change over time."""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.client = self.manager.client

    # def a1_import_members(self):
    #     """Import Members to this club"""
    #
    #     # Login as Colin (no update access to members)
    #     login_and_go_to_club_menu(
    #         manager=self.manager,
    #         org_id=SUNSHINE_ID,
    #         user=self.manager.colin,
    #         test_description="Login as Colin and go to club menu. Colin doesn't have update access to members.",
    #         test_name=f"Login as Colin and go to club menu for {club_names[SUNSHINE_ID]}",
    #         reverse_result=False,
    #     )
    #
    #     # Go to Members tab
    #     club_menu_go_to_tab(
    #         manager=self.manager,
    #         tab="members",
    #         title_id="id_member_list_tab",
    #         test_name=f"Go to Members tab as Colin for {club_names[SUNSHINE_ID]}",
    #         test_description="Starting from the dashboard of Club Menu we click on the Members tab "
    #         "and confirm that we get there.",
    #     )
    #
    #     ok = not bool(self.manager.selenium_wait_for("t_member_tab_add", timeout=5))
    #
    #     self.manager.save_results(
    #         status=ok,
    #         output=f"Clicked on Membership tab for {club_names[SUNSHINE_ID]} as Colin. Shouldn't get the Add sub-tab. "
    #         f"Outcome: {ok}",
    #         test_name=f"Colin cannot add members for {club_names[SUNSHINE_ID]}",
    #         test_description=f"Colin goes to the members tab for {club_names[SUNSHINE_ID]}. "
    #         f"He shouldn't see Add as an option as he doesn't have access.",
    #     )
    #
    #     # Login as Eric
    #     login_and_go_to_club_menu(
    #         manager=self.manager,
    #         org_id=SUNSHINE_ID,
    #         user=self.manager.eric,
    #         test_description="Login as Eric (admin) and go to club menu",
    #         test_name="Login as Eric and go to club menu",
    #         reverse_result=False,
    #     )
    #
    #     # Go to Members tab
    #     club_menu_go_to_tab(
    #         manager=self.manager,
    #         tab="members",
    #         title_id="id_member_list_tab",
    #         test_name=f"Go to Members tab as Eric for {club_names[SUNSHINE_ID]}",
    #         test_description="Starting from the dashboard of Club Menu we click on the Members tab "
    #         "and confirm that we get there.",
    #     )
    #
    #     ok = bool(self.manager.selenium_wait_for("t_member_tab_add"))
    #
    #     self.manager.save_results(
    #         status=ok,
    #         output=f"Clicked on Membership tab for {club_names[SUNSHINE_ID]} as Eric (admin). Should get the Add sub-tab. "
    #         f"Outcome: {ok}",
    #         test_name=f"Eric can add members for {club_names[SUNSHINE_ID]}",
    #         test_description=f"Eric goes to the members tab for {club_names[SUNSHINE_ID]}. "
    #         f"He should see Add as an option as he does have access.",
    #     )
    #
    #     # Import from MPC
    #     # Click Add
    #     self.manager.selenium_wait_for("t_member_tab_add").click()
    #     # Click MPC Import
    #     self.manager.selenium_wait_for("t_mpc_import").click()
    #     # Click Save
    #     self.manager.selenium_wait_for("t_mpc_import_save").click()
    #
    #     ok = bool(self.manager.selenium_wait_for_text("Import Complete", "members", 20))
    #
    #     self.manager.save_results(
    #         status=ok,
    #         output=f"Ran MPC import for {club_names[SUNSHINE_ID]} as Eric (admin). Got 'Import Complete'"
    #         f"Outcome: {ok}",
    #         test_name=f"Eric imports members from MPC for {club_names[SUNSHINE_ID]}",
    #         test_description=f"Eric imports members from MPC for {club_names[SUNSHINE_ID]}. "
    #         f"He should be able to do this successfully.",
    #     )

    def a2_import_members_csv(self):
        """Import members from CSV files"""

        # Get bridge club
        fantasy_bc = Organisation.objects.filter(name="Fantasy Bridge Club").first()

        # Login as Alan
        login_and_go_to_club_menu(
            manager=self.manager,
            org_id=fantasy_bc.org_id,
            user=self.manager.alan,
            test_description="Login as Alan (admin) and go to club menu",
            test_name="Login as Alan and go to club menu",
            reverse_result=False,
        )

        # Go to Members tab
        club_menu_go_to_tab(
            manager=self.manager,
            tab="members",
            title_id="id_member_list_tab",
            test_name=f"Go to Members tab as Alan for {fantasy_bc}",
            test_description="Starting from the dashboard of Club Menu we click on the Members tab "
            "and confirm that we get there.",
        )

        ok = bool(self.manager.selenium_wait_for("t_member_tab_add"))

        self.manager.save_results(
            status=ok,
            output=f"Clicked on Membership tab for {fantasy_bc} as Alan (admin). Should get the Add sub-tab. "
            f"Outcome: {ok}",
            test_name=f"Alan can add members for {fantasy_bc}",
            test_description=f"Alan goes to the members tab for {fantasy_bc}. "
            f"He should see Add as an option as he does have access.",
        )

        # Have to use real data for now as need valid ABF numbers
        data = [
            {"system_number": 136131, "first_name": "David", "last_name": "Fryda"},
            {"system_number": 101, "first_name": "Betty", "last_name": "Bunting"},
            {"system_number": 24732, "first_name": "Pauline", "last_name": "Gumby"},
            {"system_number": 35238, "first_name": "Warren", "last_name": "Lazer"},
        ]

        # Basic success
        _csv_upload_helper(
            self.manager,
            data[0]["system_number"],
            data[0]["first_name"],
            data[0]["last_name"],
            fantasy_bc,
            "Valid data",
        )

        # Invalid ABF
        _csv_upload_helper(
            self.manager,
            data[1]["system_number"],
            data[1]["first_name"],
            data[1]["last_name"],
            fantasy_bc,
            "Invalid ABF No",
            expect_to_fail=True,
        )
