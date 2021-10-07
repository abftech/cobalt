"""Tests for things a member is likely to do that uses payments"""

import time

from django.urls import reverse

from payments.payments_views.core import get_balance
from payments.models import MemberTransaction
from payments import forms

from payments.tests.common_functions import (
    setup_auto_top_up,
    check_balance_for_user,
    check_last_transaction_for_user,
)
from tests.test_manager import CobaltTestManager


class MemberTransfer:
    """Member transfer related activities.

    These tests cover scenarios where a member transfers money to another
    member. This can trigger manual or auto top ups and different validation
    rules.
    """

    def __init__(self, manager: CobaltTestManager):
        self.manager = manager
        self.client = self.manager.client

    def a1_member_transfer_with_sufficient_funds(self):
        """Transfer to another member with sufficient funds in account"""

        # Set up betty to transfer to
        betty = self.manager.get_user(username="101")
        alan = self.manager.test_user  # shorthand

        # Check Alan's balance before

        alan_expected_initial_balance = 400.0
        check_balance_for_user(
            manager=self.manager,
            user=alan,
            expected_balance=alan_expected_initial_balance,
            test_name="Check initial balance for Alan",
            test_description="This is the initial check of Alan's balance before we process the transfer.",
        )

        #################################

        # Check Betty's balance before
        betty_expected_initial_balance = 404.44
        check_balance_for_user(
            manager=self.manager,
            user=betty,
            expected_balance=betty_expected_initial_balance,
            test_name="Check initial balance for Betty",
            test_description="This is the initial check of Betty's balance before we process the transfer.",
        )

        ################################

        # Transfer from Alan to Betty
        desc = "Al to Betty, test transfer"
        amt = 54.45

        # Test the form
        form_data = {
            "transfer_to": betty,
            "amount": amt,
            "description": desc,
        }

        form = forms.MemberTransfer(data=form_data)

        self.manager.save_results(
            status=form.is_valid(),
            test_name="Check member Transfer Form - Alan to Betty",
            output=form.errors,
            test_description="Test the form is valid for this transfer. Doesn't actually do the transfer.",
        )

        #############################

        # Test the view - actually do the transfer
        view_data = {
            "transfer_to": betty.id,
            "amount": amt,
            "description": desc,
        }

        url = reverse("payments:member_transfer")
        response = self.client.post(url, view_data)

        self.manager.save_results(
            status=response.status_code,
            test_name="Execute member transfer - Alan to Betty",
            test_description="Use the view to actually perform a transfer from Alan to Betty. Alan should have sufficient funds for this to go through.",
        )

        #############################

        # Check after

        # Betty side
        check_last_transaction_for_user(
            manager=self.manager,
            user=betty,
            tran_desc=desc,
            tran_amt=amt,
            test_name="Execute member transfer - Alan to Betty. Betty transaction",
            other_member=alan,
            test_description="Check that Betty's latest transaction is the transfer from Alan.",
        )

        #############################

        # Alan side
        check_last_transaction_for_user(
            manager=self.manager,
            user=alan,
            tran_desc=desc,
            tran_amt=-amt,
            test_name="Execute member transfer - Alan to Betty. Alan transaction",
            other_member=betty,
            test_description="Check that Alan's latest transaction is the transfer to Betty.",
        )

        #############################

        # Check Alan's balance after
        check_balance_for_user(
            manager=self.manager,
            user=alan,
            expected_balance=alan_expected_initial_balance - amt,
            test_name="Execute member transfer - Alan to Betty. Alan balance",
            test_description="Check that Alan's balance after the transfer to Betty is correct.",
        )

        ##############################

        # Check Betty's balance after
        check_balance_for_user(
            manager=self.manager,
            user=betty,
            expected_balance=betty_expected_initial_balance + amt,
            test_name="Execute member transfer - Alan to Betty. Betty balance",
            test_description="Check that Betty's balance after the transfer from Alan is correct.",
        )

    ##############################

    def a2_member_auto_top_up_enable(self):
        """Enable auto top up"""
        alan = self.manager.test_user
        betty = self.manager.get_user(username="101")

        # set it ip
        setup_auto_top_up(self.manager)
        self.manager.save_results(
            status=True,
            test_name="Turn on auto top up for Alan",
            output="Hardcoded success. Tests follow.",
            test_description="This step sets up auto top up using Selenium. Pass here just means that it didn't crash, subsequent steps check if it was really successful.",
        )

        ##############################

        # Check auto top up
        test = bool(alan.stripe_auto_confirmed)
        self.manager.save_results(
            status=test,
            test_name="Check auto top up flag turned on for Alan",
            output="Expected stripe_auto_confirmed=True",
            test_description="Looks at user object to see if auto top up has been enabled.",
        )

        ##############################

        # Check auto top up amount
        expected_amount = 100.0
        test = alan.auto_amount == expected_amount
        self.manager.save_results(
            status=test,
            test_name="Check auto top up amount for Alan",
            output=f"Expected ${expected_amount}, got ${alan.auto_amount}",
            test_description="Looks at user object to see that auto top up amount is set to expected value.",
        )

        #############################

        # Trigger auto top up
        amt = 500.0
        desc = "Trigger Auto"
        view_data = {
            "transfer_to": betty.id,
            "amount": amt,
            "description": desc,
        }

        url = reverse("payments:member_transfer")
        response = self.client.post(url, view_data)

        self.manager.save_results(
            status=response.status_code,
            test_name="Manual transfer to trigger auto top up - Alan to Betty",
            test_description="This transaction should trigger an auto top up event for Alan.",
        )

        #############################

        # Give Stripe time to call us back
        time.sleep(5)

        # Check after

        # Betty side
        betty_tran = (
            MemberTransaction.objects.filter(member=betty)
            .order_by("-created_date")
            .first()
        )

        if betty_tran.description == desc and float(betty_tran.amount) == amt:
            test_result = True
        else:
            test_result = False

        result = f"Expected {amt} and '{desc}'. Got {betty_tran.amount} and '{betty_tran.description}'"

        self.manager.save_results(
            status=test_result,
            test_name="Member transfer triggering auto top up - Alan to Betty. Betty transaction",
            output=result,
            test_description="Check Betty's latest transaction is the transfer from Alan.",
        )

        ############################

        alan_balance = get_balance(alan)

        test_result = alan_balance == 345.55

        self.manager.save_results(
            status=test_result,
            test_name="Manual transfer triggering auto top up - Alan to Betty. Alan's balance",
            output=f"Expected ${alan_balance}. Got ${alan_balance}",
            test_description="tba",
        )
