"""Tests for things a member is likely to do that uses payments"""

import time

from django.urls import reverse
from selenium.webdriver.support.select import Select

from notifications.tests.common_functions import check_email_sent
from payments.views.core import get_balance
from payments.models import MemberTransaction
from payments import forms

from payments.tests.integration.common_functions import (
    setup_auto_top_up,
    check_balance_for_user,
    check_last_transaction_for_user,
    stripe_manual_payment_screen,
)
from tests.test_manager import CobaltTestManagerIntegration


class MemberTransfer:
    """Member transfer related activities.

    These tests cover scenarios where a member transfers money to another
    member. This can trigger manual or auto top ups and different validation
    rules.
    """

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager
        self.client = self.manager.client
        self.driver = self.manager.driver

        # Log user in
        self.manager.login_user(self.manager.test_user)

    ##############################

    def a3_member_auto_top_up_enable(self):
        """Enable auto top up"""
        alan = self.manager.alan
        betty = self.manager.betty

        # Log Alan in
        self.manager.login_user(alan)

        # set it up
        setup_auto_top_up(self.manager)
        self.manager.save_results(
            status=True,
            test_name="Turn on auto top up for Alan",
            output="Hardcoded success. Tests follow.",
            test_description="This step sets up auto top up using Selenium. Pass here just means that it didn't crash, subsequent steps check if it was really successful.",
        )

        ###############################
        # IMPORTANT!!!!
        #
        # Users seem to now be cached so we need to reload Alan again
        ################################
        alan = self.manager.get_user(username="100")
        self.manager.login_user(alan)

        ##############################

        # Check auto top up
        test = alan.stripe_auto_confirmed == "On"
        self.manager.save_results(
            status=test,
            test_name="Check auto top up flag turned on for Alan",
            output=f"Expected stripe_auto_confirmed='On'. Found: {alan.stripe_auto_confirmed}.",
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
        amt = 1000.0
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

        # alan side
        # alan_tran = (
        #     MemberTransaction.objects.filter(member=alan)
        #     .order_by("-created_date")
        #     .first()
        # )

        test_result = alan_balance == 345.55

        self.manager.save_results(
            status=test_result,
            test_name="Manual transfer triggering auto top up - Alan to Betty. Alan's balance",
            output=f"Expected ${alan_balance}. Got ${alan_balance}",
            test_description="tba",
        )
