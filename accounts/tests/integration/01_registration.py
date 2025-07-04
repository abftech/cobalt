import time

from django.urls import reverse
from selenium.webdriver.common.by import By

from tests.test_manager import CobaltTestManagerIntegration


def invalid_data_on_form(manager, test_name, test_description, element, error):
    """Check for an error in the form"""

    # Submit form
    manager.selenium_wait_for("id_signup").click()

    # check error
    msg = manager.driver.find_element(By.ID, element)
    validation_message = msg.get_attribute("validationMessage")

    # Check we get an error
    ok = error in validation_message

    manager.save_results(
        status=ok,
        test_name=test_name,
        output=f"Looked for '{error}' in {element}. Full text was '{validation_message}'. {ok}",
        test_description=test_description,
    )


class Registration:
    """Tests for things on the user registration page"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager

    def a1_basic_validate(self):

        # Get registration url
        registration_url = self.manager.base_url + reverse("accounts:register")

        # Connect to page
        self.manager.driver.get(registration_url)

        # enter ABF number - Julie Guthrie
        self.manager.selenium_wait_for_clickable("id_username").send_keys("620254")

        # click on email address field to trigger lookup
        self.manager.selenium_wait_for_clickable("id_email").click()

        invalid_data_on_form(
            manager=self.manager,
            test_name="Incomplete registration form no email",
            test_description="Test for registration form not having email address",
            element="id_email",
            error="Please fill",
        )

        # enter invalid email - no @
        self.manager.selenium_wait_for("id_email").send_keys("I am a hamster")

        invalid_data_on_form(
            manager=self.manager,
            test_name="Invalid email address. No @",
            test_description="Test for registration form having invalid email address",
            element="id_email",
            error="Please include an '@'",
        )

        # No need to test more examples, basically testing HTML5 validation here.

        # enter valid email
        self.manager.selenium_wait_for("id_email").clear()
        self.manager.selenium_wait_for("id_email").send_keys("a@b.com")

        invalid_data_on_form(
            manager=self.manager,
            test_name="Missing password1",
            test_description="Test for registration form not having password1",
            element="id_password1",
            error="Please fill",
        )

        # enter password1
        self.manager.selenium_wait_for("id_password1").send_keys("F1shcake")

        invalid_data_on_form(
            manager=self.manager,
            test_name="Missing password2",
            test_description="Test for registration form not having password2",
            element="id_password2",
            error="Please fill",
        )

        # self.manager.sleep()
        #
        # # enter password2, different from password1
        # self.manager.selenium_wait_for("id_password2").send_keys("Pencil5467")
        # self.manager.selenium_wait_for("id_signup").click()
        #
        # string = "The two password fields"
        # error = self.manager.selenium_wait_for("id_password2_errors").text
        # ok = string in error
        #
        # self.manager.save_results(
        #     status=ok,
        #     test_name="Non-matching passwords",
        #     output=f"Looked for '{string}' in '{error}'. {ok}",
        #     test_description="Enter two different passwords and check the validation works",
        # )
