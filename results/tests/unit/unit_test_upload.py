from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory

from organisations.forms import ResultsFileForm
from organisations.models import Organisation
from organisations.views.club_menu_tabs.results import upload_results_file_valid
from results.models import PlayerSummaryResult, ResultsFile
from tests.test_manager import CobaltTestManagerUnit

TEST_FILE_PATH = "results/tests/test_files"


class ResultsFileUploadTests:
    """Tests for the results file upload path in upload_results_file_valid().

    Covers each supported event type (MP_PAIRS, CROSS_IMP, BUTLER_PAIRS — both Howell
    and Mitchell variants), plus rejection of unsupported event types and invalid XML.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.club = Organisation.objects.get(pk=1)
        self.factory = RequestFactory()

    def _upload_file(self, filename, content=None):
        """Build a form with a real (or synthetic) file and call upload_results_file_valid.

        Patches tab_results_htmx so template rendering is not required in unit tests.
        Returns the response from upload_results_file_valid.
        """
        request = self.factory.post("/fake/")
        request.user = self.manager.alan

        if content is None:
            with open(f"{TEST_FILE_PATH}/{filename}", "rb") as f:
                content = f.read()

        uploaded = SimpleUploadedFile(filename, content)
        form = ResultsFileForm(data={}, files={"results_file": uploaded})

        with patch(
            "organisations.views.club_menu_tabs.results.tab_results_htmx",
            return_value=HttpResponse("ok"),
        ):
            return upload_results_file_valid(request, form, self.club)

    def _count_results_files(self):
        return ResultsFile.objects.filter(organisation=self.club).count()

    def _latest_results_file(self):
        return ResultsFile.objects.filter(organisation=self.club).latest("created_at")

    def test_01_mp_pairs_mitchell_upload(self):
        """MP_PAIRS Mitchell (two-field) file uploads correctly."""
        before = self._count_results_files()
        self._upload_file("mp_pairs_mitchell.xml")
        after = self._count_results_files()

        rf = self._latest_results_file()
        player_count = PlayerSummaryResult.objects.filter(results_file=rf).count()

        self.manager.save_results(
            status=(
                after == before + 1
                and rf.event_type == ResultsFile.EventType.MP_PAIRS
                and rf.description
                and rf.event_date
                and player_count > 0
            ),
            test_name="MP_PAIRS Mitchell upload",
            test_description="Upload a two-field MP_PAIRS file and check ResultsFile and PlayerSummaryResult records are created correctly",
            output=f"ResultsFile count {before}->{after}, event_type={rf.event_type}, description='{rf.description}', event_date={rf.event_date}, player_records={player_count}",
        )

    def test_02_mp_pairs_howell_upload(self):
        """MP_PAIRS Howell (single-field) file uploads correctly."""
        before = self._count_results_files()
        self._upload_file("mp_pairs_howell.xml")
        after = self._count_results_files()

        rf = self._latest_results_file()
        player_count = PlayerSummaryResult.objects.filter(results_file=rf).count()

        self.manager.save_results(
            status=(
                after == before + 1
                and rf.event_type == ResultsFile.EventType.MP_PAIRS
                and rf.description
                and rf.event_date
                and player_count > 0
            ),
            test_name="MP_PAIRS Howell upload",
            test_description="Upload a single-field MP_PAIRS file and check records are created correctly",
            output=f"ResultsFile count {before}->{after}, event_type={rf.event_type}, player_records={player_count}",
        )

    def test_03_cross_imp_howell_upload(self):
        """CROSS_IMP Howell (single-field) file uploads correctly."""
        before = self._count_results_files()
        self._upload_file("cross_imp_howell.xml")
        after = self._count_results_files()

        rf = self._latest_results_file()
        player_count = PlayerSummaryResult.objects.filter(results_file=rf).count()
        imp_score_used = all(
            "IMP" in (p.result_string or "")
            for p in PlayerSummaryResult.objects.filter(results_file=rf)
        )

        self.manager.save_results(
            status=(
                after == before + 1
                and rf.event_type == ResultsFile.EventType.CROSS_IMP
                and rf.description
                and rf.event_date
                and player_count > 0
                and imp_score_used
            ),
            test_name="CROSS_IMP Howell upload",
            test_description="Upload a single-field CROSS_IMP file and check records use IMP scoring",
            output=f"ResultsFile count {before}->{after}, event_type={rf.event_type}, player_records={player_count}, IMP scores={imp_score_used}",
        )

    def test_04_butler_howell_upload(self):
        """BUTLER_PAIRS Howell (single-field) file uploads correctly."""
        before = self._count_results_files()
        self._upload_file("butler_howell.xml")
        after = self._count_results_files()

        rf = self._latest_results_file()
        player_count = PlayerSummaryResult.objects.filter(results_file=rf).count()

        self.manager.save_results(
            status=(
                after == before + 1
                and rf.event_type == ResultsFile.EventType.BUTLER_PAIRS
                and rf.description
                and rf.event_date
                and player_count > 0
            ),
            test_name="BUTLER_PAIRS Howell upload",
            test_description="Upload a single-field BUTLER_PAIRS file and check records are created correctly",
            output=f"ResultsFile count {before}->{after}, event_type={rf.event_type}, player_records={player_count}",
        )

    def test_05_butler_mitchell_upload(self):
        """BUTLER_PAIRS Mitchell (two-field) file uploads correctly."""
        before = self._count_results_files()
        self._upload_file("butler_mitchell.xml")
        after = self._count_results_files()

        rf = self._latest_results_file()
        player_count = PlayerSummaryResult.objects.filter(results_file=rf).count()

        self.manager.save_results(
            status=(
                after == before + 1
                and rf.event_type == ResultsFile.EventType.BUTLER_PAIRS
                and rf.description
                and rf.event_date
                and player_count > 0
            ),
            test_name="BUTLER_PAIRS Mitchell upload",
            test_description="Upload a two-field BUTLER_PAIRS file and check records are created correctly",
            output=f"ResultsFile count {before}->{after}, event_type={rf.event_type}, player_records={player_count}",
        )

    def test_06_unsupported_event_type(self):
        """File with unsupported EVENT_TYPE is rejected with a clean error; no records persist."""
        before = self._count_results_files()
        self._upload_file("notsupported.xml")
        after = self._count_results_files()

        self.manager.save_results(
            status=(after == before),
            test_name="Unsupported event type rejected",
            test_description="Upload a file with EVENT_TYPE='NOTSUP' and verify the ResultsFile record is deleted and no player records are created",
            output=f"ResultsFile count {before}->{after} (expected no change)",
        )

    def test_07_invalid_xml(self):
        """A file that is not valid XML is rejected; no records persist."""
        before = self._count_results_files()
        self._upload_file("invalid.xml", content=b"this is not xml at all")
        after = self._count_results_files()

        self.manager.save_results(
            status=(after == before),
            test_name="Invalid XML rejected",
            test_description="Upload a file with invalid XML content and verify the ResultsFile record is deleted and no player records are created",
            output=f"ResultsFile count {before}->{after} (expected no change)",
        )
