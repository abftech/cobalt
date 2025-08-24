from time import sleep

import boto3
from django.urls import reverse
from django.utils.timezone import now
from selenium.common import NoSuchElementException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from accounts.models import UnregisteredUser, UserAdditionalInfo, User
from cobalt.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME
from organisations.models import Organisation, ClubMemberLog, MemberClubDetails
from tests.test_manager import CobaltTestManagerIntegration


def _block_email(email):
    """helper to block and email"""

    # Create AWS API client
    client = boto3.client(
        "sesv2",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME,
    )

    client.put_suppressed_destination(EmailAddress=email, Reason="BOUNCE")

    # Add to User
    for user in User.objects.filter(email=email):
        additional_user, _ = UserAdditionalInfo.objects.get_or_create(user=user)
        additional_user.email_hard_bounce = True
        additional_user.email_hard_bounce_reason = "Testing"
        additional_user.email_hard_bounce_date = now()
        additional_user.save()

    # Add to contacts/unreg
    for detail in MemberClubDetails.objects.filter(email=email):
        detail.email_hard_bounce = True
        detail.email_hard_bounce_reason = "Testing"
        detail.email_hard_bounce_date = now()
        detail.save()


class UserSearch:
    """Tests for User and Unregistered user searches (both members and contacts)
    Also tests removing blocks from AWS SES emails.

    We set up dummy blocks and remove them.

    We use:
        Alan Admin - User
        Sherlock Balvenie - Unregistered User with ABF number
        David Attenborough - Contact (Unregistered User without ABF number)

    """

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.manager.login_user(self.manager.alan)

        # Set alan's email address and a block
        self.manager.alan.email = "alan.admin@17ways.com.au"
        self.manager.alan.save()
        _block_email(self.manager.alan.email)

        # Create users registered by Fantasy Bridge Club
        self.club = Organisation.objects.get(pk=10)

        # Create Unregistered user
        self.unreg_user = UnregisteredUser()
        self.unreg_user.system_number = 123456789
        self.unreg_user.first_name = "Sherlock"
        self.unreg_user.last_name = "Balvenie"
        self.unreg_user.origin = "Manual"
        self.unreg_user.internal_system_number = False
        self.unreg_user.added_by_club = self.club
        self.unreg_user.last_updated_by = self.manager.alan
        self.unreg_user.save()

        # create a new member details record
        MemberClubDetails(
            club=self.club,
            system_number=123456789,
            email="sherlock.balvenie@example.com",
        ).save()

        _block_email("sherlock.balvenie@example.com")

        # Create Contact
        self.contact = UnregisteredUser()
        self.contact.system_number = 23456789
        self.contact.first_name = "David"
        self.contact.last_name = "Attenborough"
        self.contact.origin = "Manual"
        self.contact.internal_system_number = True
        self.contact.added_by_club = self.club
        self.contact.last_updated_by = self.manager.alan
        self.contact.save()

        MemberClubDetails(
            club=self.club,
            system_number=23456789,
            email="david.attenborough@example.com",
            membership_status=MemberClubDetails.MEMBERSHIP_STATUS_CONTACT,
        ).save()

        _block_email("david.attenborough@example.com")

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

    def a4_user_email_block(self):
        """add an email block and check we can remove it"""

        # Add the block
        UserAdditionalInfo(user=self.manager.alan, email_hard_bounce=True).save()

        # Go to the profile
        url = self.manager.base_url + reverse(
            "accounts:public_profile", kwargs={"pk": self.manager.alan.id}
        )
        self.manager.driver.get(url)

        # despite Alan Admin's claim to be an uber admin, he shouldn't see the email info
        try:
            self.manager.driver.find_element(By.ID, "id_email_block")
            ok = False
        except NoSuchElementException:
            ok = True

        self.manager.save_results(
            status=ok,
            test_name="Check normal users don't see the email admin parts of public profile",
            test_description="As Alan we look up ourselves, shouldn't see email admin",
        )

        # now login as a true global admin
        mark = User.objects.filter(username="Mark").first()
        self.manager.login_user(mark)

        # Go to profile
        self.manager.driver.get(url)

        # Remove the block
        remove_block = self.manager.selenium_wait_for_clickable("id_remove_block")
        remove_block.click()

        # Wait for response
        self.manager.selenium_wait_for_text("Email", "id_email_block")

        # give it a seconds
        sleep(1)

        alan = UserAdditionalInfo.objects.filter(user=self.manager.alan).first()

        self.manager.save_results(
            status=alan.email_hard_bounce is False,
            test_name="Remove block from user Alan",
            test_description="Go to Alan's public profile and remove the block",
            output=f"Alan additional info email_hard_bounce is {alan.email_hard_bounce}",
        )

    def a5_unreg_user_email_block(self):
        """add an email block and check we can remove it"""

        # login as Alan
        self.manager.login_user(self.manager.alan)

        # Go to the profile
        url = self.manager.base_url + reverse(
            "accounts:unregistered_public_profile", kwargs={"pk": self.unreg_user.id}
        )
        self.manager.driver.get(url)

        # despite Alan Admin's claim to be an uber admin, he shouldn't see the email info
        try:
            self.manager.driver.find_element(By.ID, "id_email_block")
            ok = False
        except NoSuchElementException:
            ok = True

        self.manager.save_results(
            status=ok,
            test_name="Check normal users don't see the email admin parts of unreg public profile",
            test_description="As Alan we look up unregistered user 'Balvenie', shouldn't see email admin",
        )

        # now login as a true global admin
        mark = User.objects.filter(username="Mark").first()
        self.manager.login_user(mark)

        # Go to profile
        self.manager.driver.get(url)

        # scroll to bottom
        self.manager.selenium_scroll_to_bottom()

        # Remove the block
        remove_block = self.manager.selenium_wait_for_clickable(
            "t_remove_block_membership"
        )
        remove_block.click()

        # give it a second
        sleep(2)

        balvenie = MemberClubDetails.objects.filter(system_number=123456789).first()

        self.manager.save_results(
            status=not balvenie.email_hard_bounce,
            test_name="Remove block from unreg user Balvenie",
            test_description="Go to Balvenie's public profile and remove the block",
            output=f"Balvenie member club details email_hard_bounce is {balvenie.email_hard_bounce}",
        )

    def a6_contact_email_block(self):
        """Remove a block from a contact"""

        # login as Alan
        self.manager.login_user(self.manager.alan)

        # Go to the profile
        url = self.manager.base_url + reverse(
            "accounts:unregistered_public_profile", kwargs={"pk": self.contact.id}
        )
        self.manager.driver.get(url)

        # despite Alan Admin's claim to be an uber admin, he shouldn't see the email info
        try:
            self.manager.driver.find_element(By.ID, "id_email_block")
            ok = False
        except NoSuchElementException:
            ok = True

        self.manager.save_results(
            status=ok,
            test_name="Check normal users don't see the email admin parts of contact public profile",
            test_description="As Alan we look up contact user 'David Attenborough', shouldn't see email admin",
        )

        # now login as a true global admin
        mark = User.objects.filter(username="Mark").first()
        self.manager.login_user(mark)

        # Go to profile
        self.manager.driver.get(url)

        # scroll to bottom
        self.manager.selenium_scroll_to_bottom()

        # Remove the block
        remove_block = self.manager.selenium_wait_for_clickable(
            "t_remove_block_membership"
        )
        remove_block.click()

        # give it a second
        sleep(2)

        contact = MemberClubDetails.objects.filter(system_number=23456789).first()

        self.manager.save_results(
            status=not contact.email_hard_bounce,
            test_name="Remove block from contact Attenborough",
            test_description="Go to Attenborough's public profile and remove the block",
            output=f"Attenborough member club details email_hard_bounce is {contact.email_hard_bounce}",
        )
