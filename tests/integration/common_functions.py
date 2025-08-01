"""Common functions used across all tests"""

import time

from selenium.common.exceptions import StaleElementReferenceException

from tests.test_manager import CobaltTestManagerIntegration


def cobalt_htmx_user_search(
    manager: CobaltTestManagerIntegration,
    search_button_id: str,
    user_system_id: str,
    search_id="",
):
    """Drive Cobalt HTMX user search to add a user

    Args:
        manager: standard manager object
        search_button_id: id of the button to press to bring up the search
        search_id: Optional field name required for some searches, if the form adds this on
        user_system_id: which user to add
    """

    # User Search button
    manager.selenium_wait_for_clickable(search_button_id).click()

    # Wait for modal to appear and enter system number
    system_number = manager.selenium_wait_for_clickable(
        f"id_system_number{search_id}", 10
    )

    try:
        system_number.click()
    except AttributeError:
        print("############")
        print("Couldn't find user in cobalt_htmx_user_search")
        print("Sleeping so you can check the problem")
        print("############")
        manager.sleep()
    system_number.send_keys(user_system_id)

    # Wait for search results and click ok
    manager.selenium_wait_for_clickable(f"id_cobalt_search_ok{search_id}").click()
