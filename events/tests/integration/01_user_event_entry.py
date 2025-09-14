from time import sleep

from django.urls import reverse

from accounts.models import TeamMate
from events.models import Event, Congress
from events.tests.integration.common_functions import (
    enter_event_and_check,
    enter_event_then_pay_and_check,
)
from payments.models import MemberTransaction, OrganisationTransaction
from payments.views.core import update_account, get_balance
from tests.test_manager import CobaltTestManagerIntegration


class EventEntry:
    """Tests for event entry through UI"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.client = self.manager.client

        # Login Keith
        self.manager.login_user(self.manager.keith)

        # Set up Congress - My Big Congress
        self.congress = Congress.objects.get(pk=1)
        self.congress.payment_method_bank_transfer = True
        self.congress.payment_method_cash = True
        self.congress.payment_method_cheques = True
        self.congress.payment_method_off_system_pp = True
        self.congress.bank_transfer_details = "Gold bars"
        self.congress.cheque_details = "Pay to cash"
        self.congress.save()

        # Set up event - My Big Congress, Pairs
        self.pairs_event = Event.objects.get(pk=1)
        self.teams_event = Event.objects.get(pk=2)

        self.pairs_entry_url = self.manager.base_url + reverse(
            "events:enter_event", kwargs={"congress_id": 1, "event_id": 1}
        )
        self.teams_entry_url = self.manager.base_url + reverse(
            "events:enter_event", kwargs={"congress_id": 1, "event_id": 2}
        )

        # set up team mates for Keith
        TeamMate(
            user=self.manager.lucy, team_mate=self.manager.keith, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.morris, team_mate=self.manager.keith, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.natalie, team_mate=self.manager.keith, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.penelope, team_mate=self.manager.keith, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.keith, team_mate=self.manager.lucy, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.keith, team_mate=self.manager.morris, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.keith, team_mate=self.manager.natalie, make_payments=True
        ).save()
        TeamMate(
            user=self.manager.keith, team_mate=self.manager.penelope, make_payments=True
        ).save()

        # Give Keith some money
        update_account(
            member=self.manager.keith,
            amount=1000.0,
            description="Cash",
            payment_type="Refund",
        )

    def a1_pairs_entry(self):
        """Simple pairs entry scenarios"""

        # Both Bridge Credits
        enter_event_and_check(
            test_name="Pairs entry for Keith - pays for both",
            test_description="Keith enters event and pays for Lucy",
            test_instance=self,
            event=self.pairs_event,
            entry_url=self.pairs_entry_url,
            player_list=[[self.manager.lucy, "my-system-dollars", "Paid"]],
        )

        # Bank Transfer
        enter_event_and_check(
            test_name="Pairs entry for Keith - Bridge Credits and Bank Transfer",
            test_description="Keith enters event and sets Lucy to Bank Transfer",
            test_instance=self,
            event=self.pairs_event,
            entry_url=self.pairs_entry_url,
            player_list=[[self.manager.lucy, "bank-transfer", "Pending Manual"]],
        )

        # cash and bank transfer
        enter_event_and_check(
            test_name="Pairs entry for Keith - Cash and Bank Transfer",
            test_description="Keith enters event with cash and sets Lucy to Bank Transfer",
            test_instance=self,
            event=self.pairs_event,
            entry_url=self.pairs_entry_url,
            player_list=[[self.manager.lucy, "bank-transfer", "Pending Manual"]],
            player0_payment_type="cash",
        )

        # Go to checkout and pay using stripe
        # Empty Keith's bank account
        update_account(
            member=self.manager.keith,
            amount=-get_balance(self.manager.keith),
            description="Empty Keith out",
            payment_type="Refund",
        )

        enter_event_then_pay_and_check(
            test_name="Pairs entry for Keith - Insufficient funds",
            test_description="Keith enters event and pays for himself and Lucy with Stripe",
            test_instance=self,
            event=self.pairs_event,
            entry_url=self.pairs_entry_url,
            player_list=[[self.manager.lucy, "my-system-dollars", "Paid", True]],
        )

    def a2_teams_entry(self):
        """Simple teams entry scenarios"""

        # Give Keith some money
        update_account(
            member=self.manager.keith,
            amount=1000.0,
            description="Cash",
            payment_type="Refund",
        )

        # All Bridge Credits
        enter_event_and_check(
            test_name="Teams entry for Keith - pays for all",
            test_description="Keith enters event and pays for everyone",
            test_instance=self,
            event=self.teams_event,
            entry_url=self.teams_entry_url,
            player_list=[
                [self.manager.lucy, "my-system-dollars", "Paid"],
                [self.manager.morris, "my-system-dollars", "Paid"],
                [self.manager.natalie, "my-system-dollars", "Paid"],
            ],
        )

    def a3_cancel_entry(self):
        """Test cancelling an entry and ensuring it works properly for COB-822"""

        # We already have an entry and we are logged in as Keith
        event = Event.objects.last()

        # Go to event entry
        self.manager.driver.get(
            f"{self.manager.base_url}/events/congress/event/change-entry/{event.congress.id}/{event.id}"
        )

        # Cancel it
        self.manager.selenium_wait_for_clickable("t_withdraw").click()

        # Click confirm
        self.manager.selenium_wait_for_clickable("t_confirm").click()

        # Give it a sec
        sleep(1)

        # Check event_id is applied to transaction
        last_tran = MemberTransaction.objects.last()
        last_org_tran = OrganisationTransaction.objects.last()

        self.manager.save_results(
            status=last_tran.event_id == event.id
            and last_org_tran.event_id == event.id,
            test_name="Withdraw from event and check event_id is applied to transaction",
            test_description="Check we add the event_id when a user withdraws",
            output=f"{last_tran.event_id=} {last_org_tran.event_id=}",
        )
