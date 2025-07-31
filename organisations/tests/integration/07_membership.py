from time import sleep

from django.urls import reverse
from docutils.nodes import description
from selenium.webdriver import ActionChains

from accounts.models import User
from organisations.models import Organisation
from payments.models import MemberTransaction
from payments.tests.integration.common_functions import setup_auto_top_up
from tests.test_manager import CobaltTestManagerIntegration


class ClubMembership:
    """Tests for club memberships"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.client = self.manager.client

    def a2_double_payment(self):
        """There was a problem with users double clicking the payment
        button. This test was written to address this"""

        # Switch on auto top up for Betty Bunting
        # Log betty in
        self.manager.login_user(self.manager.betty)

        # set it up
        setup_auto_top_up(self.manager)

        # Set balance to $20
        last_trans = MemberTransaction.objects.filter(member=self.manager.betty).last()
        last_trans.balance = 20
        last_trans.save()

        betty = self.manager.get_user(username=self.manager.betty.system_number)

        ##############################
        # Check auto top up
        ##############################
        test = betty.stripe_auto_confirmed == "On"
        self.manager.save_results(
            status=test,
            test_name="Membership - Turn on auto top up for Betty",
            output=f"Expected stripe_auto_confirmed='On'. Found: {betty.stripe_auto_confirmed}.",
            test_description="Looks at user object to see if auto top up has been enabled.",
        )

        # Quit if it failed - nothing else will work
        if not test:
            print("Test FAILED - SKIPPING FURTHER TESTS")
            return

        # Login as Mark
        mark = User.objects.filter(username="Mark").first()
        self.manager.login_user(mark)

        self.manager.save_results(
            status=True,
            test_name="Membership - login as admin",
            output=f"Logged in as Mark - got {mark}",
            test_description="Login as user to do admin tasks",
        )

        # Go to club menu for payments bridge club
        payments_bc = Organisation.objects.filter(name="Payments Bridge Club").first()
        url = self.manager.base_url + reverse(
            "organisations:club_menu", kwargs={"club_id": payments_bc.id}
        )
        self.manager.driver.get(url)

        # Set club to full club admin - tried to use the UI but couldn't get the checkbox to work
        payments_bc.full_club_admin = True
        payments_bc.save()

        self.manager.save_results(
            status=payments_bc.full_club_admin,
            test_name="Membership - set Payments Bridge Club to Full Club Admin",
            output=f"Expected True, Found {payments_bc.full_club_admin=}",
            test_description="Set to full club admin",
        )

        # click id_tab_members to go to the members view
        self.manager.selenium_wait_for_clickable("id_tab_members").click()

        self.manager.save_results(
            status=True,
            test_name="Membership - go to Member view",
        )

        # Click t_member_tab_add to go to the add member view
        self.manager.selenium_wait_for_clickable("t_member_tab_add").click()

        self.manager.save_results(
            status=True,
            test_name="Membership - go to Add member",
        )

        # click t_member_add_individual_member to add an individual
        self.manager.selenium_wait_for_clickable(
            "t_member_add_individual_member"
        ).click()

        self.manager.save_results(
            status=True,
            test_name="Membership - go to Add individual member",
        )

        # type bunt into id_member_last_name_search
        self.manager.selenium_wait_for("id_member_last_name_search").send_keys("bunt")

        # sometimes stalls so waste second
        sleep(1)
        self.manager.selenium_wait_for("id_member_last_name_search").send_keys("ing")

        self.manager.save_results(
            status=True,
            test_name="Membership - search for Betty Bunting",
        )

        # Click on add button
        self.manager.selenium_wait_for(
            f"t_user_search_result_{betty.system_number}"
        ).click()

        self.manager.save_results(
            status=True,
            test_name="Membership - click on Add",
        )

        # Click on save button
        self.manager.selenium_wait_for("id-save-button-text").click()
        self.manager.selenium_wait_for("t_show_details").click()

        self.manager.save_results(
            status=True,
            test_name="Membership - click on save",
        )

        # Now log in as Betty so we can double click the button
        self.manager.login_selenium_user(betty)

        self.manager.save_results(
            status=True,
            test_name="Membership - login as Betty to pay for membership",
        )

        # Go to profile
        url = self.manager.base_url + reverse("accounts:user_profile")
        self.manager.driver.get(url)

        self.manager.save_results(
            status=True,
            test_name="Membership - go to Betty's profile",
        )

        # Click on pay now two times
        pay_button = self.manager.selenium_wait_for_clickable("t_initiate_payment")

        ActionChains(self.manager.driver).double_click(pay_button).perform()

        self.manager.save_results(
            status=True,
            test_name="Membership - Double click on payment in Betty's profile",
        )

        # Check payments - get payments that are membership fees - expect only one
        payments = (
            MemberTransaction.objects.filter(member=betty)
            .filter(type="Club Membership")
            .count()
        )

        self.manager.save_results(
            status=payments == 1,
            test_name="Membership - check only one payment happens on double click",
            output=f"Expected 1, Found {payments}",
            test_description="Double click on payment in the profile and check that only one payment goes through",
        )
