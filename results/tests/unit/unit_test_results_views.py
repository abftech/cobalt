from django.http import HttpResponse
from django.urls import reverse
from unittest.mock import patch

from organisations.models import Organisation
from organisations.forms import ResultsFileForm
from django.core.files.uploadedfile import SimpleUploadedFile
from organisations.views.club_menu_tabs.results import upload_results_file_valid
from results.models import ResultsFile
from results.views.usebio import (
    players_from_usebio,
    boards_from_usebio,
    parse_usebio_file,
)
from tests.test_manager import CobaltTestManagerUnit

TEST_FILE_PATH = "results/tests/test_files"


class ResultsViewsTests:
    """Tests for results view functions in results/views/results_views.py.

    Covers: MP pairs summary (single-field and two-field), MP pairs player detail,
    MP pairs board traveller, IMP summary, IMP player detail, IMP board traveller,
    Butler summary/detail/board, and show_results_for_club_htmx endpoint.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.club = Organisation.objects.get(pk=1)
        self.manager.login_test_client(self.manager.alan)

    def _upload_file(self, filename):
        """Upload a results XML file and return the created ResultsFile."""
        with open(f"{TEST_FILE_PATH}/{filename}", "rb") as f:
            content = f.read()

        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/fake/")
        request.user = self.manager.alan

        uploaded = SimpleUploadedFile(filename, content)
        form = ResultsFileForm(data={}, files={"results_file": uploaded})

        with patch(
            "organisations.views.club_menu_tabs.results.tab_results_htmx",
            return_value=HttpResponse("ok"),
        ):
            upload_results_file_valid(request, form, self.club)

        return ResultsFile.objects.filter(organisation=self.club).latest("created_at")

    def _get(self, url):
        return self.manager.client.get(url)

    def _post(self, url, data):
        return self.manager.client.post(url, data)

    # ------------------------------------------------------------------ #
    # MP_PAIRS — two-field Mitchell                                        #
    # ------------------------------------------------------------------ #

    def test_01_mp_pairs_two_field_summary(self):
        """MP_PAIRS two-field summary view returns 200."""
        rf = self._upload_file("mp_pairs_mitchell.xml")
        url = reverse(
            "results:usebio_mp_pairs_results_summary_view",
            kwargs={"results_file_id": rf.id},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="MP pairs two-field summary view",
            test_description="Upload a two-field MP_PAIRS file and verify the summary page returns HTTP 200",
            output=f"HTTP {response.status_code} for {url}",
        )

    def test_02_mp_pairs_two_field_player_detail(self):
        """MP_PAIRS two-field player detail view returns 200 for every player."""
        rf = self._upload_file("mp_pairs_mitchell.xml")
        players = players_from_usebio(rf)
        failures = []
        for pair_id in players:
            url = reverse(
                "results:usebio_mp_pairs_details_view",
                kwargs={"results_file_id": rf.id, "pair_id": pair_id},
            )
            rc = self._get(url).status_code
            if rc != 200:
                failures.append(f"{pair_id}={rc}")
        self.manager.save_results(
            status=not failures,
            test_name="MP pairs two-field player detail views",
            test_description="For each pair in a two-field Mitchell file, verify the player detail page returns HTTP 200",
            output=f"Checked {len(players)} pairs. Failures: {failures or 'none'}",
        )

    def test_03_mp_pairs_two_field_board_traveller(self):
        """MP_PAIRS two-field board traveller view returns 200 for first player and all boards."""
        rf = self._upload_file("mp_pairs_mitchell.xml")
        players = players_from_usebio(rf)
        boards = boards_from_usebio(rf)
        pair_id = players[0]
        failures = []
        for board in boards:
            url = reverse(
                "results:usebio_mp_pairs_board_view",
                kwargs={
                    "results_file_id": rf.id,
                    "pair_id": pair_id,
                    "board_number": board,
                },
            )
            rc = self._get(url).status_code
            if rc != 200:
                failures.append(f"board {board}={rc}")
        self.manager.save_results(
            status=not failures,
            test_name="MP pairs two-field board traveller views",
            test_description="For each board in a two-field Mitchell file, verify the board traveller page returns HTTP 200",
            output=f"Checked {len(boards)} boards for pair {pair_id}. Failures: {failures or 'none'}",
        )

    # ------------------------------------------------------------------ #
    # MP_PAIRS — single-field Howell                                       #
    # ------------------------------------------------------------------ #

    def test_04_mp_pairs_single_field_summary(self):
        """MP_PAIRS single-field Howell summary view returns 200."""
        rf = self._upload_file("mp_pairs_howell.xml")
        url = reverse(
            "results:usebio_mp_pairs_results_summary_view",
            kwargs={"results_file_id": rf.id},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="MP pairs single-field summary view",
            test_description="Upload a single-field Howell MP_PAIRS file and verify the summary page returns HTTP 200",
            output=f"HTTP {response.status_code} for {url}",
        )

    def test_05_mp_pairs_single_field_player_detail(self):
        """MP_PAIRS single-field player detail view returns 200 for every player."""
        rf = self._upload_file("mp_pairs_howell.xml")
        players = players_from_usebio(rf)
        failures = []
        for pair_id in players:
            url = reverse(
                "results:usebio_mp_pairs_details_view",
                kwargs={"results_file_id": rf.id, "pair_id": pair_id},
            )
            rc = self._get(url).status_code
            if rc != 200:
                failures.append(f"{pair_id}={rc}")
        self.manager.save_results(
            status=not failures,
            test_name="MP pairs single-field player detail views",
            test_description="For each pair in a single-field Howell file, verify the player detail page returns HTTP 200",
            output=f"Checked {len(players)} pairs. Failures: {failures or 'none'}",
        )

    def test_06_mp_pairs_single_field_board_traveller(self):
        """MP_PAIRS single-field board traveller view returns 200 for first player and all boards."""
        rf = self._upload_file("mp_pairs_howell.xml")
        players = players_from_usebio(rf)
        boards = boards_from_usebio(rf)
        pair_id = players[0]
        failures = []
        for board in boards:
            url = reverse(
                "results:usebio_mp_pairs_board_view",
                kwargs={
                    "results_file_id": rf.id,
                    "pair_id": pair_id,
                    "board_number": board,
                },
            )
            rc = self._get(url).status_code
            if rc != 200:
                failures.append(f"board {board}={rc}")
        self.manager.save_results(
            status=not failures,
            test_name="MP pairs single-field board traveller views",
            test_description="For each board in a single-field Howell file, verify the board traveller page returns HTTP 200",
            output=f"Checked {len(boards)} boards for pair {pair_id}. Failures: {failures or 'none'}",
        )

    # ------------------------------------------------------------------ #
    # CROSS_IMP — Howell                                                   #
    # ------------------------------------------------------------------ #

    def test_07_cross_imp_summary(self):
        """CROSS_IMP summary view returns 200."""
        rf = self._upload_file("cross_imp_howell.xml")
        url = reverse(
            "results:usebio_mp_pairs_results_summary_view",
            kwargs={"results_file_id": rf.id},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="CROSS_IMP summary view",
            test_description="Upload a CROSS_IMP file and verify the summary page returns HTTP 200",
            output=f"HTTP {response.status_code} for {url}",
        )

    def test_08_cross_imp_player_detail(self):
        """CROSS_IMP player detail view returns 200 for every player."""
        rf = self._upload_file("cross_imp_howell.xml")
        usebio = parse_usebio_file(rf)["EVENT"]
        failures = []
        for item in usebio["PARTICIPANTS"]["PAIR"]:
            pair_id = item["PAIR_NUMBER"]
            url = reverse(
                "results:imp_pairs_details_view",
                kwargs={"results_file_id": rf.id, "pair_id": pair_id},
            )
            rc = self._get(url).status_code
            if rc != 200:
                failures.append(f"{pair_id}={rc}")
        pair_count = len(usebio["PARTICIPANTS"]["PAIR"])
        self.manager.save_results(
            status=not failures,
            test_name="CROSS_IMP player detail views",
            test_description="For each pair in a CROSS_IMP file, verify the IMP player detail page returns HTTP 200",
            output=f"Checked {pair_count} pairs. Failures: {failures or 'none'}",
        )

    def test_09_cross_imp_board_traveller(self):
        """CROSS_IMP board traveller view returns 200 for first player and all boards."""
        rf = self._upload_file("cross_imp_howell.xml")
        usebio = parse_usebio_file(rf)["EVENT"]
        boards = boards_from_usebio(rf)
        pair_id = usebio["PARTICIPANTS"]["PAIR"][0]["PAIR_NUMBER"]
        failures = []
        for board in boards:
            url = reverse(
                "results:imp_board_view",
                kwargs={
                    "results_file_id": rf.id,
                    "pair_id": pair_id,
                    "board_number": board,
                },
            )
            rc = self._get(url).status_code
            if rc != 200:
                failures.append(f"board {board}={rc}")
        self.manager.save_results(
            status=not failures,
            test_name="CROSS_IMP board traveller views",
            test_description="For each board in a CROSS_IMP file, verify the IMP board traveller page returns HTTP 200",
            output=f"Checked {len(boards)} boards for pair {pair_id}. Failures: {failures or 'none'}",
        )

    # ------------------------------------------------------------------ #
    # BUTLER_PAIRS — Mitchell                                              #
    # ------------------------------------------------------------------ #

    def test_10_butler_summary(self):
        """BUTLER_PAIRS summary view returns 200."""
        rf = self._upload_file("butler_mitchell.xml")
        url = reverse(
            "results:usebio_mp_pairs_results_summary_view",
            kwargs={"results_file_id": rf.id},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="BUTLER_PAIRS summary view",
            test_description="Upload a BUTLER_PAIRS Mitchell file and verify the summary page returns HTTP 200",
            output=f"HTTP {response.status_code} for {url}",
        )

    def test_11_butler_player_detail(self):
        """BUTLER_PAIRS player detail view returns 200 for the first player."""
        rf = self._upload_file("butler_mitchell.xml")
        usebio = parse_usebio_file(rf)["EVENT"]
        pair_id = usebio["PARTICIPANTS"]["PAIR"][0]["PAIR_NUMBER"]
        url = reverse(
            "results:imp_pairs_details_view",
            kwargs={"results_file_id": rf.id, "pair_id": pair_id},
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="BUTLER_PAIRS player detail view",
            test_description="Upload a BUTLER_PAIRS file and verify the IMP player detail page returns HTTP 200",
            output=f"HTTP {response.status_code} for pair {pair_id}",
        )

    def test_12_butler_board_traveller(self):
        """BUTLER_PAIRS board traveller view returns 200 for first player and first board."""
        rf = self._upload_file("butler_mitchell.xml")
        usebio = parse_usebio_file(rf)["EVENT"]
        boards = boards_from_usebio(rf)
        pair_id = usebio["PARTICIPANTS"]["PAIR"][0]["PAIR_NUMBER"]
        url = reverse(
            "results:imp_board_view",
            kwargs={
                "results_file_id": rf.id,
                "pair_id": pair_id,
                "board_number": boards[0],
            },
        )
        response = self._get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="BUTLER_PAIRS board traveller view",
            test_description="Upload a BUTLER_PAIRS file and verify the IMP board traveller page returns HTTP 200",
            output=f"HTTP {response.status_code} for pair {pair_id}, board {boards[0]}",
        )

    # ------------------------------------------------------------------ #
    # show_results_for_club_htmx                                           #
    # ------------------------------------------------------------------ #

    def test_13_show_results_for_club_htmx(self):
        """show_results_for_club_htmx POST returns 200 for a valid club."""
        url = reverse("results:show_results_for_club_htmx")
        response = self._post(url, {"club_id": self.club.id})
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="show_results_for_club_htmx",
            test_description="POST to show_results_for_club_htmx with a valid club_id and verify HTTP 200",
            output=f"HTTP {response.status_code} for club_id={self.club.id}",
        )

    # ------------------------------------------------------------------ #
    # Login required redirect                                              #
    # ------------------------------------------------------------------ #

    def test_14_results_summary_requires_login(self):
        """Results summary redirects to login when not authenticated."""
        rf = self._upload_file("mp_pairs_mitchell.xml")
        self.manager.client.logout()
        url = reverse(
            "results:usebio_mp_pairs_results_summary_view",
            kwargs={"results_file_id": rf.id},
        )
        response = self._get(url)
        # Re-login for subsequent tests
        self.manager.login_test_client(self.manager.alan)
        self.manager.save_results(
            status=response.status_code in (302, 301),
            test_name="Results summary requires login",
            test_description="Access the summary view without authentication and verify it redirects to the login page",
            output=f"HTTP {response.status_code} (expected redirect 302)",
        )
