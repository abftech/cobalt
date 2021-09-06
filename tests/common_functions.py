"""Common functions used across all tests"""
import time

from selenium.common.exceptions import StaleElementReferenceException

from tests.test_manager import CobaltTestManager
from termcolor import colored


def cobalt_htmx_user_search(
    manager: CobaltTestManager,
    search_button_id: str,
    user_system_id: str,
    search_id="",
):
    """Drive Cobalt HTMX user search to add a user

    Args:
        manager: standard manager object
        search_button_id: id of the button to press to bring up the search
        search_id: search id set for this user search
        user_system_id: which user to add
    """
    print(colored(f"Starting user search for {user_system_id}", "blue"))

    # User Search button - could be reloaded, so try to fix if stale
    try:
        manager.selenium_wait_for_clickable(search_button_id).click()
        print(colored("   Got search first time", "grey"))
    except StaleElementReferenceException:
        print("   Stale Element Reference")
        time.sleep(3)
        manager.selenium_wait_for_clickable(search_button_id).click()
        print("   Got search second time")

    print(f"   Waiting for id_system_number{search_id} to appear")

    # Wait for modal to appear and enter system number in
    system_number = manager.selenium_wait_for_clickable("id_system_number" + search_id)
    system_number.click()

    print(f"   Found it. Sending {user_system_id}")

    system_number.send_keys(user_system_id)

    print("   Sent, Clicking on search button")

    # click on system number search
    manager.driver.find_element_by_id(
        "id_button_system_number_search" + search_id
    ).click()

    print("   Clicked, waiting for ok")

    # Wait for search results and click ok
    manager.selenium_wait_for_clickable("id_cobalt_search_ok" + search_id).click()

    print("   Ok found and clicked")
    print(colored("Search successful", "blue"))
