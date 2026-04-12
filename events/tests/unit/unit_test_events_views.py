from django.urls import reverse

from organisations.models import Organisation
from tests.test_manager import CobaltTestManagerUnit

# Congress pk=1 "Online Summer Congress 2021" is Published in test data.
# Event pk=1 is Matchpoint Swiss Pairs (not open — renders event_closed.html).
TEST_CONGRESS_ID = 1
TEST_EVENT_ID = 1


class EventsViewsTests:
    """Unit tests for user-facing event views in events/views/views.py

    Covers: congress_listing, congress_listing_logged_out,
    congress_listing_data_htmx, view_congress, checkout, view_events,
    view_event_entries, enter_event (event closed path), enter_event_success,
    enter_event_payment_fail, view_event_partnership_desk,
    show_congresses_for_club_htmx, and login-required redirects.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.alan = manager.alan
        self.club = Organisation.objects.get(pk=1)
        self.manager.login_test_client(self.alan)

    def _get(self, url):
        return self.manager.client.get(url)

    def _post(self, url, data):
        return self.manager.client.post(url, data)

    # ------------------------------------------------------------------ #
    # congress_listing                                                     #
    # ------------------------------------------------------------------ #

    def test_01_congress_listing_authenticated(self):
        """GET /events/ returns HTTP 200 for an authenticated user."""
        url = reverse("events:congress_listing")
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="congress_listing — authenticated",
            test_description="GET /events/ for a logged-in user should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    def test_02_congress_listing_logged_out(self):
        """GET /events/ redirects to the logged-out listing for unauthenticated users."""
        self.manager.client.logout()
        url = reverse("events:congress_listing")
        response = self._get(url)
        # Re-login for subsequent tests
        self.manager.login_test_client(self.alan)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="congress_listing — logged out",
            test_description="GET /events/ without authentication should return HTTP 200 (shows the logged-out congress listing)",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # congress_listing_data_htmx                                          #
    # ------------------------------------------------------------------ #

    def test_03_congress_listing_data_htmx(self):
        """POST to congress-listing-data returns HTTP 200."""
        url = reverse("events:congress_listing_data_htmx")
        response = self._post(url, {"reverse_list": ""})
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="congress_listing_data_htmx POST",
            test_description="POST to congress-listing-data endpoint should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # view_congress                                                        #
    # ------------------------------------------------------------------ #

    def test_04_view_congress_authenticated(self):
        """GET /events/congress/view/<id>/ returns HTTP 200 for an authenticated user."""
        url = reverse("events:view_congress", kwargs={"congress_id": TEST_CONGRESS_ID})
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="view_congress — authenticated",
            test_description="GET view_congress for an authenticated user should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    def test_05_view_congress_logged_out(self):
        """GET view_congress returns HTTP 200 for unauthenticated users (Published congress)."""
        self.manager.client.logout()
        url = reverse("events:view_congress", kwargs={"congress_id": TEST_CONGRESS_ID})
        response = self._get(url)
        self.manager.login_test_client(self.alan)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="view_congress — logged out",
            test_description="GET view_congress without authentication should return HTTP 200 for a Published congress",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # checkout                                                             #
    # ------------------------------------------------------------------ #

    def test_06_checkout_get(self):
        """GET /events/congress/checkout returns HTTP 200 (empty basket)."""
        url = reverse("events:checkout")
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="checkout GET",
            test_description="GET checkout with an empty basket should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    def test_07_checkout_requires_login(self):
        """GET /events/congress/checkout redirects unauthenticated users."""
        self.manager.client.logout()
        url = reverse("events:checkout")
        response = self._get(url)
        self.manager.login_test_client(self.alan)
        self.manager.save_results(
            status=response.status_code in (301, 302),
            test_name="checkout requires login",
            test_description="GET checkout without authentication should redirect to login",
            output=f"HTTP {response.status_code} (expected 302)",
        )

    # ------------------------------------------------------------------ #
    # view_events                                                          #
    # ------------------------------------------------------------------ #

    def test_08_view_events_get(self):
        """GET /events/view returns HTTP 200."""
        url = reverse("events:view_events")
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="view_events GET",
            test_description="GET view_events for an authenticated user should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # view_event_entries                                                   #
    # ------------------------------------------------------------------ #

    def test_09_view_event_entries_get(self):
        """GET view_event_entries returns HTTP 200."""
        url = reverse(
            "events:view_event_entries",
            kwargs={"congress_id": TEST_CONGRESS_ID, "event_id": TEST_EVENT_ID},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="view_event_entries GET",
            test_description="GET view_event_entries should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # enter_event                                                          #
    # ------------------------------------------------------------------ #

    def test_10_enter_event_get(self):
        """GET enter_event returns a valid response for an authenticated user.

        Depending on whether the event is open and whether the user is already
        entered, the view may return 200 (entry form, event-closed page, or
        event-full page) or 302 (redirect to edit entry if already entered).
        Both are valid authenticated responses.
        """
        url = reverse(
            "events:enter_event",
            kwargs={"congress_id": TEST_CONGRESS_ID, "event_id": TEST_EVENT_ID},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code in (200, 302),
            test_name="enter_event GET — authenticated user",
            test_description="GET enter_event for an authenticated user should return HTTP 200 or 302 (redirect if already entered)",
            output=f"HTTP {response.status_code}",
        )

    def test_11_enter_event_requires_login(self):
        """GET enter_event redirects unauthenticated users."""
        self.manager.client.logout()
        url = reverse(
            "events:enter_event",
            kwargs={"congress_id": TEST_CONGRESS_ID, "event_id": TEST_EVENT_ID},
        )
        response = self._get(url)
        self.manager.login_test_client(self.alan)
        self.manager.save_results(
            status=response.status_code in (301, 302),
            test_name="enter_event requires login",
            test_description="GET enter_event without authentication should redirect to login",
            output=f"HTTP {response.status_code} (expected 302)",
        )

    # ------------------------------------------------------------------ #
    # enter_event_success                                                  #
    # ------------------------------------------------------------------ #

    def test_12_enter_event_success_get(self):
        """GET enter_event_success returns HTTP 200 (delegates to view_events)."""
        url = reverse("events:enter_event_success")
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="enter_event_success GET",
            test_description="GET enter_event_success should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # enter_event_payment_fail                                             #
    # ------------------------------------------------------------------ #

    def test_13_enter_event_payment_fail_get(self):
        """GET enter_event_payment_fail returns HTTP 200."""
        url = reverse("events:enter_event_payment_fail")
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="enter_event_payment_fail GET",
            test_description="GET enter_event_payment_fail should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # view_event_partnership_desk                                          #
    # ------------------------------------------------------------------ #

    def test_14_view_event_partnership_desk_get(self):
        """GET view_event_partnership_desk returns HTTP 200."""
        url = reverse(
            "events:view_event_partnership_desk",
            kwargs={"congress_id": TEST_CONGRESS_ID, "event_id": TEST_EVENT_ID},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="view_event_partnership_desk GET",
            test_description="GET view_event_partnership_desk should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # show_congresses_for_club_htmx                                        #
    # ------------------------------------------------------------------ #

    def test_15_show_congresses_for_club_htmx(self):
        """POST show_congresses_for_club_htmx with a valid club_id returns HTTP 200."""
        url = reverse("events:show_congresses_for_club_htmx")
        response = self._post(url, {"club_id": self.club.id})
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="show_congresses_for_club_htmx POST",
            test_description="POST show_congresses_for_club_htmx with a valid club_id should return HTTP 200",
            output=f"HTTP {response.status_code}",
        )
