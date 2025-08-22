from django.urls import reverse
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from accounts.models import UnregisteredUser
from organisations.club_admin_core import add_contact_with_system_number
from organisations.models import Organisation, ClubMemberLog, MemberClubDetails
from tests.test_manager import CobaltTestManagerIntegration


class UserSearch:
    """Tests for User and Unregistered user searches (both members and contacts)"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.manager.login_user(self.manager.alan)

        # Create users registered by Fantasy Bridge Club
        club = Organisation.objects.get(pk=10)

        # Create Unregistered user
        unreg_user = UnregisteredUser()
        unreg_user.system_number = 123456789
        unreg_user.first_name = "Sherlock"
        unreg_user.last_name = "Balvenie"
        unreg_user.origin = "Manual"
        unreg_user.internal_system_number = False
        unreg_user.added_by_club = club
        unreg_user.last_updated_by = self.manager.alan
        unreg_user.save()

        # create a new member details record
        add_contact_with_system_number(
            club,
            unreg_user.system_number,
        )

        # Create Contact
        contact = UnregisteredUser()
        contact.system_number = 23456789
        contact.first_name = "David"
        contact.last_name = "Attenborough"
        contact.origin = "Manual"
        contact.internal_system_number = True
        contact.added_by_club = club
        contact.last_updated_by = self.manager.alan
        contact.save()

        # create a new member details record
        add_contact_with_system_number(
            club,
            contact.system_number,
        )

    def a1_user_search(self):
        """search for a user and check it matches"""

        # Find the search field
        search = self.manager.selenium_wait_for_clickable("search_string")

        # put in Alan and hit enter
        search.send_keys("alan")
        search.send_keys(Keys.RETURN)

        # Look for expected text
        alan_text = self.manager.selenium_find_text_on_page("Alan Admin")
        alan_no = self.manager.selenium_find_text_on_page("ABF Number: 100")

        self.manager.save_results(
            status=alan_no and alan_text,
            test_name="Search for user by name",
            test_description="Enter Alan in search box and check we find him",
        )

        # Click on link to go to profile
        self.manager.selenium_wait_for_clickable("t_search_link_7").click()

        ok = self.manager.driver.current_url.find("accounts/public-profile/7") > 0

        self.manager.save_results(
            status=ok,
            test_name="Click link to go to public profile",
            test_description="Click the link on the search results to view Alan's public profile",
        )

    def a2_unregistered_search(self):
        """search for an unregistered user who is an ABF member and check it matches"""

        # Find the search field
        search = self.manager.selenium_wait_for_clickable("search_string")

        # put in Balvenie and hit enter
        search.send_keys("balvenie")
        search.send_keys(Keys.RETURN)

        # Look for expected text
        sherlock_text = self.manager.selenium_find_text_on_page("Sherlock Balvenie")
        sherlock_no = self.manager.selenium_find_text_on_page("ABF Number: 123456789")

        self.manager.save_results(
            status=sherlock_no and sherlock_text,
            test_name="Search for unregistered user by name",
            test_description="Enter Balvenie in search box and check we find him",
        )

        # Click on link to go to profile
        self.manager.driver.find_element(By.CLASS_NAME, "t_unreg").click()

        # Check we got a profile
        ok = (
            self.manager.driver.current_url.find("accounts/unregistered_public-profile")
            > 0
        )

        self.manager.save_results(
            status=ok,
            test_name="Click link to go to public profile of unregistered user",
            test_description="Click the link on the search results to view Sherlock's public profile",
        )

    def a3_contact_search(self):
        """Search for a contact who is an unregistered user with an internal ABF number"""

        # Create contact
        data = {
            "club_id": 10,
            "save": "INTERNAL",
            "first_name": "Horatio",
            "last_name": "Nelson",
        }
        url = self.manager.base_url + reverse(
            "organisations:club_admin_add_contact_manual_htmx"
        )
        status, response = self.manager.htmx_post(url, data)

        self.manager.save_results(
            status=status,
            test_name="Add contact to Fantasy Bridge Club",
            test_description="Use HTMX fragment to add a contact",
        )

        # Check contact is in logs
        log_entry = ClubMemberLog.objects.last()

        # Get membership record
        unreg = UnregisteredUser.all_objects.last()
        membership_details = MemberClubDetails.objects.last()

        ok = (
            log_entry.description == "Contact created (manual)"
            and membership_details.system_number == unreg.system_number
        )

        self.manager.save_results(
            status=ok,
            test_name="Check contact for Fantasy Bridge Club",
            test_description="Use HTMX fragment to add a contact",
            output=f"{unreg=} {membership_details=} {log_entry=} {ok=}",
        )

        # Now try the search
        # Find the search field
        search = self.manager.selenium_wait_for_clickable("search_string")

        # put in Horatio and hit enter
        search.send_keys("horat")
        search.send_keys(Keys.RETURN)

        # Look for expected text
        horatio_text = self.manager.selenium_find_text_on_page("Horatio Nelson")

        self.manager.save_results(
            status=horatio_text,
            test_name="Search for contact by name",
            test_description="Enter Horatio in search box and check we find him",
        )

        # Click on link to go to profile
        self.manager.driver.find_element(By.CLASS_NAME, "t_unreg").click()

        # Check we got a profile
        ok = (
            self.manager.driver.current_url.find("accounts/unregistered_public-profile")
            > 0
        )

        self.manager.save_results(
            status=ok,
            test_name="Click link to go to public profile of contact",
            test_description="Click the link on the search results to view Horatio's public profile",
        )
