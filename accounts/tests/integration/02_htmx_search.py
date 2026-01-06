from time import sleep

from django.urls import reverse

from accounts.models import User
from tests.integration.common_functions import cobalt_htmx_user_search
from tests.test_manager import CobaltTestManagerIntegration


def _search_ff_helper(
    test_name,
    manager,
    url,
    search_id,
    match_id,
    confirm_id,
    name_id,
    id_id,
    modal_id=None,
):
    """helper to test inline forms for fiona freckle"""

    # Go to page
    manager.driver.get(url)

    # If we are a modal then open it
    if modal_id:
        manager.selenium_wait_for_clickable(modal_id).click()

    # enter last name - first letters match both
    manager.selenium_wait_for_clickable(search_id).send_keys("fr")

    # Should get a match for both
    ff = manager.selenium_wait_for_text("Fiona", f"{match_id}12")
    finn = manager.selenium_wait_for_text("Finn", f"{match_id}33")

    success = bool(ff and finn)
    manager.save_results(
        status=success,
        test_name=f"{test_name} - Last Name both match",
        output=f"{success}",
        test_description="Enter 'fr' into last_name field. Expect to match on Fiona and Finn",
    )

    # click on Fiona to bring up confirm dialog
    manager.selenium_wait_for_clickable(f"{match_id}{manager.fiona.id}").click()

    # Click ok
    manager.selenium_wait_for_clickable(confirm_id).click()

    # Check fields update - once you pick someone it should update the fields on the screen
    user_name = manager.selenium_wait_for(name_id)
    user_id = manager.selenium_wait_for(id_id)

    success = (
        user_name.text == "Fiona Freckle".upper()
        and int(user_id.text) == manager.fiona.id
    )

    manager.save_results(
        status=success,
        test_name=f"{test_name} - Click updates web page",
        output=f"Expected user_name and user_id to be set. Looked for: 'FIONA FRECKLE' Found: '{user_name.text=}'. Looked for: '{manager.fiona.id=}' Found: {user_id.text=}",
        test_description="After the search - click on name and check it is updated",
    )


def _search_self_helper(
    test_name, manager, url, expected_to_work, search_id, match_id, modal_id=None
):
    """Helper for searching for yourself"""

    # Connect to page
    manager.driver.get(url)

    # If we are a modal then open it
    if modal_id:
        manager.selenium_wait_for_clickable(modal_id).click()

    # enter own name - alan admin
    manager.selenium_wait_for_clickable(search_id).send_keys("admin")

    if expected_to_work:
        aa = manager.selenium_wait_for_text("Alan", match_id)
    else:
        aa = manager.selenium_wait_for_text("No Matches", match_id)

    manager.save_results(
        status=aa,
        test_name=f"{test_name} - Search for self",
        output=f"Searched for last name admin. Got {aa}",
        test_description=f"Enter 'admin' into last_name field. {expected_to_work=}",
    )


class HTMXSearch:
    """Tests for the HTMX Member search. We use a screen within tests for testing it"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.manager.login_user(self.manager.alan)

        # Create a user, so we have letters in common with Fiona
        self.finn = User(first_name="Finn", last_name="Fredrick", system_number=9999999)
        self.finn.save()

        # Get url
        self.url = self.manager.base_url + reverse("tests:htmx_search")

    def a1_test_inline_callback_ff(self):
        """Test the inline callback - search for fiona freckle"""

        _search_ff_helper(
            "Inline exclude self",
            self.manager,
            self.url,
            "id_last_name_searchinline-callback",
            "id_htmx_search_match_inline-callback",
            "id_cobalt_search_okinline-callback",
            "inline-callback-name",
            "inline-callback-id",
        )

    def a2_test_inline_callback_aa(self):
        """Test inline callback, search for yourself - should not find you"""

        _search_self_helper(
            "Inline exclude self",
            self.manager,
            self.url,
            False,
            "id_last_name_searchinline-callback",
            "name-matchesinline-callback",
            modal_id=None,
        )

    def a3_test_inline_callback_include_self_ff(self):
        """Test the inline callback include self - search for fiona freckle"""
        _search_ff_helper(
            "Inline include self",
            self.manager,
            self.url,
            "id_last_name_searchinline-callback-include-me",
            "id_htmx_search_match_inline-callback-include-me",
            "id_cobalt_search_okinline-callback-include-me",
            "inline-callback-include-me-name",
            "inline-callback-include-me-id",
        )

    def a4_test_inline_callback_include_self_aa(self):
        """Test inline callback, search for yourself - should now find you"""

        _search_self_helper(
            "Inline include self",
            self.manager,
            self.url,
            True,
            "id_last_name_searchinline-callback-include-me",
            "id_htmx_search_match_inline-callback-include-me7",
        )

    def a5_test_modal_ff(self):
        """Test the modal popup"""

        _search_ff_helper(
            "Modal exclude self",
            self.manager,
            self.url,
            "id_last_name_searchmodalCallback",
            "id_htmx_search_match_modalCallback",
            "id_cobalt_search_okmodalCallback",
            "modal-callback-name",
            "modal-callback-id",
            "id_search_button",
        )

    def a6_test_modal_aa(self):
        """Test modal, search for yourself - should not find you"""

        _search_self_helper(
            "Modal exclude self",
            self.manager,
            self.url,
            False,
            "id_last_name_searchmodalCallback",
            "name-matchesmodalCallback",
            modal_id="id_search_button",
        )

    def a7_test_modal_include_self_ff(self):
        """Test the modal popup include self"""

        _search_ff_helper(
            "Modal include self",
            self.manager,
            self.url,
            "id_last_name_searchmodalCallbackIncludeMe",
            "id_htmx_search_match_modalCallbackIncludeMe",
            "id_cobalt_search_okmodalCallbackIncludeMe",
            "modal-callback-include-me-name",
            "modal-callback-include-me-id",
            "id_search_button_self",
        )

    def a8_test_modal_include_self_aa(self):
        """Test modal, search for yourself - should now find you"""

        _search_self_helper(
            "Modal include self",
            self.manager,
            self.url,
            True,
            "id_last_name_searchmodalCallbackIncludeMe",
            "id_htmx_search_match_modalCallbackIncludeMe7",
            modal_id="id_search_button_self",
        )

    def b1_test_harness_search_by_system_number(self):
        """Test of the function cobalt_htmx_user_search used by tests to
        find a user by system number"""

        # Go to page
        self.manager.driver.get(self.url)

        cobalt_htmx_user_search(
            self.manager, "id_search_button_self", "103", "modalCallbackIncludeMe"
        )

        # no error means success
        self.manager.save_results(
            status=True,
            test_name="Search by system number",
            test_description="Call cobalt_htmx_user_search to search by system number",
        )
