from time import sleep

from django.urls import reverse

from accounts.models import User
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
        # Connect to page
        self.manager.driver.get(self.url)

        # enter own name - alan
        self.manager.selenium_wait_for_clickable(
            "id_last_name_searchinline-callback"
        ).send_keys("admin")

        # Should get no match
        aa = self.manager.selenium_wait_for_text(
            "No Matches", "name-matchesinline-callback"
        )

        self.manager.save_results(
            status=aa,
            test_name="Inline exclude self - Search for self",
            output=f"Searched for last name admin. Got {aa}",
            test_description="Enter 'admin' into last_name field. Expect no match",
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
        # Connect to page
        self.manager.driver.get(self.url)

        # enter own name - alan
        self.manager.selenium_wait_for_clickable(
            "id_last_name_searchinline-callback-include-me"
        ).send_keys("admin")

        # Should get a match
        aa = self.manager.selenium_wait_for_text(
            "Alan", "id_htmx_search_match_inline-callback-include-me7"
        )

        self.manager.save_results(
            status=aa,
            test_name="Inline include self - Search for self",
            output=f"Searched for last name admin. Got {aa}",
            test_description="Enter 'admin' into last_name field. Expect a match",
        )

    def a5_test_modal_ff(self):
        """Test the modal popup"""

        _search_ff_helper(
            "Modal exclude self",
            self.manager,
            self.url,
            "id_last_name_searchmodalCallback",
            "id_htmx_search_match_modalCallback12",
            "id_cobalt_search_okmodalCallback",
            "modal-callback-name",
            "modal-callback-id",
            "id_search_button",
        )
