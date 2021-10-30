import time

from organisations.tests.common_functions import (
    club_menu_go_to_tab,
    login_and_go_to_club_menu,
)
from tests.test_manager import CobaltTestManager

# TODO: See if these constants can be centrally stored

# State id numbers
NSW = 3
QLD = 5

# Org org_id numbers
CANBERRA_ID = 1851
TRUMPS_ID = 2259
SUNSHINE_ID = 4680
WAVERLEY_ID = 3480

# Org names
club_names = {
    CANBERRA_ID: "Canberra Bridge Club Inc",  # ACT
    TRUMPS_ID: "Trumps Bridge Centre",  # NSW
    SUNSHINE_ID: "Sunshine Coast Contract Bridge Club Inc",  # QLD
    WAVERLEY_ID: "Waverley Bridge Club",  # VIC
}


class ClubCongress:
    """Tests for club congresses"""

    def __init__(self, manager: CobaltTestManager):
        self.manager = manager
        self.client = self.manager.client

    def a1_comms_tags(self):
        """Do things with tags"""

        time.sleep(600)
