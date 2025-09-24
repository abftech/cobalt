import glob
import logging
import os
import sys
import time
import uuid
import webbrowser

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from notifications.tests.common_functions import check_email_sent

logger = logging.getLogger("cobalt")


class SimpleSelenium:
    """high level commands to control selenium. Why this doesn't exist already, I have no idea"""

    def __init__(self, base_url, browser, show, silent, password, script_file):
        """set up"""

        self.base_url = base_url
        self.silent = silent
        self.default_password = password
        self.script_file = script_file

        self.script_file_without_extension = self.script_file.split(".")[0]
        self.script_file_without_extension_printable = (
            self.script_file_without_extension.split("/")[1]
        )

        self.output_directory = (
            f"/tmp/cobalt/smoke_test/{self.script_file_without_extension}"
        )
        self.output_file = f"{self.output_directory}/smoke-test-output.html"

        # Create output directory if not already there
        os.makedirs(self.output_directory, exist_ok=True)

        # Empty output directory
        # NOTE: If scripts get retired they will still have output in the directory
        files = glob.glob(f"{self.output_directory}/*")
        for file in files:
            os.remove(file)

        # Start chrome
        options = ChromeOptions()
        options.add_argument("window-size=1600x800")
        if not show:
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")

        # Prevent notifications and don't try to save credit cards
        options.add_experimental_option(
            "prefs",
            {
                "profile.default_content_setting_values.notifications": 2,
                "autofill.credit_card_enabled": False,
            },
        )

        self.driver = webdriver.Chrome(options=options)
        url = f"{base_url}/accounts/login"

        # Store progress messages
        self.messages = []
        self.messages_summary = []
        self.screenshots = {}
        self.current_action = "Starting"
        self.title = "Smoke Test"

        self.add_message(f"Connect to {url}")

        self.driver.get(url)

    def add_message(self, message, link=None, bold=False):
        """Add a message to the report on progress"""

        if bold:
            message = mark_safe(f"<b>--{message.upper()}--</b>")

        self.messages.append(
            {"current_action": self.current_action, "message": message, "link": link}
        )

        if self.silent:
            return

        logger.info(message)

    def summarise_messages(self):
        """Once we are done, we convert the list of messages into a list of lists so we can display it better

        self.messages is a list of {"current_action": "str", "message": "str", "link": "str"}

        self.messages_summary is list of lists e.g.

        messages = [
                        {"current_action": "login", "message": "Go to /accounts/login"},
                        {"current_action": "login", "message": "Found username"},
                        {"current_action": "sleep 5", "message": "slept for 5 seconds"},
                    ]

        messages_summary = [
                        [
                            {"current_action": "login", "message": "Go to /accounts/login"},
                            {"current_action": "login", "message": "Found username"},
                        ],
                        [
                            {"current_action": "sleep 5", "message": "slept for 5 seconds"},
                        ]
                    ]
        """
        # empty summary in case we get called more than once
        self.messages_summary = []

        last_action = "DUMMY VALUE"
        row = []
        for count, item in enumerate(self.messages, start=1):
            # Add a counter for the template
            item["index"] = count
            if last_action != item["current_action"]:
                if last_action != "DUMMY VALUE":
                    self.messages_summary.append(row)
                row = []
                last_action = item["current_action"]
            row.append(item)

        self.messages_summary.append(row)

    def handle_fatal_error(self):
        """we have had a problem - show user and leave"""

        # Save a screenshot
        self.screenshot("Error")

        self.summarise_messages()

        # Build HTML page
        html = render_to_string(
            template_name="tests/simple_selenium_fail.html", context={"data": self}
        )

        # Save page
        with open(self.output_file, "w") as html_file:
            print(html, file=html_file)

        if self.silent:
            sys.exit(1)

        # Open browser and leave
        webbrowser.open(f"file://{self.output_file}")
        sys.exit(1)

    def handle_finish(self, open_output=True):
        """report on how we went"""

        # convert list of actions into a dictionary
        self.summarise_messages()

        # Build HTML page
        html = render_to_string(
            template_name="tests/simple_selenium_success.html", context={"data": self}
        )

        # Save page
        with open(self.output_file, "w") as html_file:
            print(html, file=html_file)

        if self.silent:
            sys.exit(0)

        # Open browser
        if open_output:
            webbrowser.open(f"file://{self.output_file}")

    def find_by_text(self, search_text):
        """find something with matching text"""

        try:
            match = self.driver.find_element(
                "xpath", f"//*[contains(text(), '{search_text}')]"
            )
        except NoSuchElementException:
            try:
                match = self.driver.find_element(
                    "xpath", f"//input[@value='{search_text}']"
                )
            except NoSuchElementException:
                self.add_message(f"Looked for '{search_text}' but did not find it")
                self.handle_fatal_error()

        self.add_message(f"Looked for '{search_text}' and found it")

        return match

    def press_by_text(self, search_text):
        """find something with matching text and click it"""

        matching_element = self.find_by_text(search_text)

        # Wait for clickable
        try:
            matching_element = WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable(matching_element)
            )
        except TimeoutException:
            self.add_message(f"Waited for '{search_text}' to be clickable. Timed out.")
            self.handle_fatal_error()

        matching_element.click()
        self.add_message(f"Clicked on '{search_text}'")

        self.screenshot(f"Clicked on {search_text}")

    def find_by_name(self, name):
        """find something with matching name"""

        try:
            match = self.driver.find_element("name", name)
        except NoSuchElementException:
            self.add_message(f"Looked for item with name'{name}' but did not find it")
            self.handle_fatal_error()

        self.add_message(f"Looked for item with name '{name}' and found it")

        return match

    def find_by_id(self, id):
        """find something with matching id"""

        try:
            match = self.driver.find_element("id", id)
        except NoSuchElementException:
            self.add_message(f"Looked for item with id '{id}' but did not find it")
            self.handle_fatal_error()

        self.add_message(f"Looked for item with id '{id}' and found it")

        return match

    def press_by_name(self, name):
        """find something with matching name and click it"""

        matching_element = self.find_by_name(name)
        matching_element.click()
        self.add_message(f"Clicked on '{name}'")

        self.screenshot(f"Clicked on {name}")

    def press_by_id(self, id):
        """find something with matching id and click it"""

        matching_element = self.find_by_id(id)
        matching_element.click()
        self.add_message(f"Clicked on '{id}'")

        self.screenshot(f"Clicked on {id}")

    def go_to(self, location):
        """go to a path"""

        if location[0] != "/":
            self.add_message(
                "go command must start with /. Specify only the path. e.g. '/events'"
            )
            self.handle_fatal_error()

        self.driver.get(f"{self.base_url}{location}")
        # We don't know if it works, but it should be easy enough to identify if it doesn't
        self.add_message(f"Went to '{location}'")

        self.screenshot(f"Went to {location}")

    def send_enter(self, name):
        """send the enter key to an object"""
        try:
            item = self.driver.find_element("name", name)
        except NoSuchElementException:
            self.add_message(f"Couldn't find by name: {name}")
            self.handle_fatal_error()

        item.send_keys(Keys.RETURN)
        self.add_message(f"Sent enter to '{name}'")

    def enter_value_into_field(self, identifier, value):
        """find a field and put a value in it. Can be a variable such as password"""

        # get element, won't return if not found
        element = self._super_click_get_element(identifier)

        # Wait for clickable
        try:
            matching_element = WebDriverWait(self.driver, 5).until(
                expected_conditions.element_to_be_clickable(element)
            )
        except TimeoutException:
            self.add_message(
                f"Found '{identifier}' but timed out waiting for it to be clickable."
            )
            self.handle_fatal_error()

        matching_element.send_keys(value)

        # Hide password
        if identifier.find("password") >= 0:
            value = "*********"

        self.screenshot(f"Put '{value}' into '{identifier}'")

    def screenshot(self, title):
        """grab a picture of the screen"""

        filename = f"{self.output_directory}/{uuid.uuid4()}.png"
        self.driver.save_screenshot(filename)
        self.screenshots[filename] = title

        self.add_message(f"Took a screenshot - {title}", link=filename)

    def selectpicker(self, value, name):
        """make bootstrap selectpicker have value specified. NOT FINISHED"""

        # TODO - NOT FINISHED. IT WASN"T A SELECT PICKER

        dropdown = self.driver.find_element("name", name)
        dropdown.click()
        option = self.driver.find_element(
            "css selector",
            f"ul[role=menu] a[data-normalized-text='<span class=\"text\">{value}</span>']",
        )
        option.click()
        # elem.sendKeys("American Samoa");
        # elem.sendKeys(Keys.ENTER);
        self.screenshot("temp")

    def dropdown(self, value, name):
        """choose a value from a dropdown"""

        try:
            self.driver.find_element(
                "xpath", f"//select[@name='{name}']/option[text()='{value}']"
            ).click()
        except NoSuchElementException:
            self.add_message(
                f"Tried to select '{value}' from dropdown '{name}' but couldn't"
            )
            self.handle_fatal_error()

        self.add_message(f"Selected '{value}' from dropdown '{name}'")

    def sleep(self, seconds):
        """sleep for the specified number of seconds"""

        time.sleep(seconds)
        self.add_message(f"Slept for {seconds} second(s)")

    def set_title(self, title):
        """set the title for the page"""

        self.title = title

    def login(self, username):
        """login a user"""

        # Go to login url
        self.go_to("/accounts/login")

        # Provide credentials
        self.enter_value_into_field("id_username", username)
        self.enter_value_into_field("id_password", self.default_password)

        # Take a screenshot
        self.screenshot("Logging in")

        # Login
        self.super_click("Login")

        # Check we are logged in
        self.find_by_text("Bridge Credits")

        # Take a screenshot
        self.screenshot("Logged in")

    def _super_click_by_id(self, identifier):
        """try to get element by id"""

        try:
            match = self.driver.find_element("id", identifier)
        except NoSuchElementException:
            self.add_message(
                f"Looked for item with id '{identifier}' but did not find it"
            )
            return False

        self.add_message(f"Looked for item with id '{identifier}' and found it")

        return match

    def _super_click_by_name(self, identifier):
        """try to get element by name"""

        try:
            match = self.driver.find_element("id", identifier)
        except NoSuchElementException:
            self.add_message(
                f"Looked for item with name '{identifier}' but did not find it"
            )
            return False

        self.add_message(f"Looked for item with name '{identifier}' and found it")

        return match

    def _super_click_by_text(self, identifier):
        """try to get element by text"""

        try:
            match = self.driver.find_element(
                "xpath", f"//*[contains(text(), '{identifier}')]"
            )
        except NoSuchElementException:
            self.add_message(
                f"Looked for item with text '{identifier}' but did not find it"
            )
            return False

        self.add_message(f"Looked for item with text '{identifier}' and found it")

        return match

    def _super_click_by_value(self, identifier):
        """try to get element by value"""

        try:
            match = self.driver.find_element("xpath", f"//input[@value='{identifier}']")
        except NoSuchElementException:
            self.add_message(
                f"Looked for item with value '{identifier}' but did not find it"
            )
            return False

        self.add_message(f"Looked for item with value '{identifier}' and found it")

        return match

    def _super_click_get_element(self, identifier):
        """Try to find identifier in multiple ways"""

        # Try a couple of times in case things are slow

        element = False
        retry_count = 3
        count = 0

        while not element and count < retry_count:
            count += 1

            # Try by id
            element = self._super_click_by_id(identifier)

            if element:
                return element

            # Try by name
            element = self._super_click_by_name(identifier)

            if element:
                return element

            # Try by value
            element = self._super_click_by_value(identifier)

            if element:
                return element

            # Try by text on button/link
            element = self._super_click_by_text(identifier)

            if element:
                return element

            if count < retry_count:
                self.add_message(
                    f"Didn't find '{identifier}'. Sleeping before retrying", bold=True
                )
                time.sleep(1)

        self.add_message(f"Unable to find a match for '{identifier}'", bold=True)
        self.handle_fatal_error()

    def super_click(self, identifier):
        """Try to find identifier in multiple ways"""

        # get element, won't return if not found
        element = self._super_click_get_element(identifier)

        # Wait for clickable
        try:
            matching_element = WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable(element)
            )
        except TimeoutException:
            self.add_message(
                f"Found '{identifier}' but timed out waiting for it to be clickable."
            )
            self.handle_fatal_error()

        matching_element.click()

    def check_email_to(self, sender):
        """Check for an email sent to sender"""

        status, message = check_email_sent(email_to=sender, save_results=False)

        if not status:
            self.add_message(
                f"Looked for email sent to '{sender}'. Error was '{message}'"
            )
            self.handle_fatal_error()

        self.add_message(message)

    def check_email_to_with_subject(self, sender, subject):
        """Check for an email sent to sender with subject"""

        status, message = check_email_sent(
            email_to=sender, subject_search=subject, save_results=False, email_count=20
        )

        if not status:
            self.add_message(
                f"Looked for email sent to '{sender}' with subject '{subject}'. Error was '{message}'"
            )
            self.handle_fatal_error()

        self.add_message(message)

    def check_email_to_with_body(self, sender, body_search):
        """Check for an email sent to sender with specific string in body"""

        status, message = check_email_sent(
            email_to=sender,
            body_search=body_search,
            save_results=False,
            email_count=20,
            debug=True,
        )

        if not status:
            self.add_message(
                f"Looked for email sent to '{sender}' with body containing '{body_search}'. Error was '{message}'"
            )
            self.handle_fatal_error()

        self.add_message(message)
