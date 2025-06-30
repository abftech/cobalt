"""Tests for the auto-pay cron job for memberships"""

import datetime

import stripe

from cobalt.settings import STRIPE_SECRET_KEY
from organisations.models import (
    Organisation,
    MembershipType,
    MemberMembershipType,
    MemberClubDetails,
)
from organisations.views.admin import add_club_defaults
from payments.models import (
    MemberTransaction,
    OrganisationTransaction,
    StripeTransaction,
)

from tests.test_manager import CobaltTestManagerIntegration

from organisations.management.commands.auto_pay_batch import Command
from utils.models import Lock


def _user_set_up_helper(user, club, membership_type, auto_top_up):
    """Add all the bits and pieces needed for users"""

    # create member memberships
    member_membership = MemberMembershipType(membership_type=membership_type)
    member_membership.system_number = user.system_number
    member_membership.fee = membership_type.annual_fee
    member_membership.last_modified_by = user
    member_membership.is_paid = False
    member_membership.start_date = datetime.date.today() - datetime.timedelta(days=2)
    member_membership.due_date = datetime.date.today() - datetime.timedelta(days=2)
    member_membership.auto_pay_date = datetime.date.today() - datetime.timedelta(days=2)
    member_membership.save()

    # Create Stripe customer
    if auto_top_up:
        stripe.api_key = STRIPE_SECRET_KEY
        customer = stripe.Customer.create(name=user.full_name)
        user.stripe_customer_id = customer["id"]
        user.stripe_auto_confirmed = "On"
        user.auto_amount = 50
        user.save()

        # add card using test visa data
        stripe.Customer.create_source(user.stripe_customer_id, source="tok_visa")

    # Create MemberClubDetails records
    member_club_details = MemberClubDetails(
        system_number=user.system_number, club=club, latest_membership=member_membership
    )
    member_club_details.save()


def _test_outcome_helper(manager, test_name, user, club, amount, expect_stripe):
    """helper to check the status"""

    # check what happened
    last_member_tran = MemberTransaction.objects.last()
    last_org_tran = OrganisationTransaction.objects.last()
    member_membership = MemberMembershipType.objects.filter(
        system_number=user.system_number
    ).first()

    pay_status = (
        last_member_tran.member == user
        and float(last_member_tran.amount) == -amount
        and last_member_tran.organisation == club
        and last_org_tran.organisation == club
        and float(last_org_tran.amount) == amount
        and last_org_tran.member == user
    )
    member_status = member_membership.membership_state == "CUR"

    output = f"""
    Payment status: {pay_status}. Member status: {member_status}.
    {last_member_tran=}
    Found: {last_member_tran.member=}. Expected {user=}.
    Found: {last_member_tran.amount=}. Expected: {amount=}.
    Found: {last_member_tran.organisation=}. Expected: {club=}.
    Found: {last_org_tran.organisation=}. Expected: {club=}.
    Found: {last_org_tran.amount=}. Expected: {amount=}.
    Found: {last_org_tran.member=}. Expected: {user=}.
    Found: {member_membership.membership_state}. Expected: CUR.
    """

    manager.save_results(
        status=pay_status and member_status,
        test_name=f"Auto Pay Membership batch. {test_name}",
        test_description="Test the auto_pay_memberships script",
        output=output,
    )

    # Check Stripe
    stripe_trans = StripeTransaction.objects.last()
    if expect_stripe:
        status = stripe_trans.member == user
    else:
        status = not stripe_trans or stripe_trans.member != user

    manager.save_results(
        status=status,
        test_name=f"Auto Pay Membership batch. {test_name}. Stripe Transaction",
        test_description="Check for Stripe transaction",
        output=f"Stripe transaction is {stripe_trans}. Stripe user is '{stripe_trans.member}'. Expected user is '{user}'. Expect Stripe is {expect_stripe}.",
    )


class AutoPayMembershipsTests:
    """Unit tests for auto-paying membership fees"""

    def __init__(self, manager: CobaltTestManagerIntegration):
        self.manager = manager

        # Create a club
        self.club = Organisation(name="Auto Pay Club", org_id="Bob")
        self.club.secretary = self.manager.alan
        self.club.type = "Club"
        self.club.state = "NSW"
        self.club.full_club_admin = True
        self.club.save()
        add_club_defaults(self.club)

        # Create membership type
        self.membership_type = MembershipType(organisation=self.club, name="name")
        self.membership_type.annual_fee = 47.56
        self.membership_type.last_modified_by = self.manager.alan
        self.membership_type.membership_status = "Due"
        self.membership_type.save()

    def test_01_sufficient_funds(self):
        """User has funds to pay"""

        # Set up users
        _user_set_up_helper(
            self.manager.alan, self.club, self.membership_type, auto_top_up=False
        )

        # Put enough money into account
        MemberTransaction(
            member=self.manager.alan, amount=10, balance=500, type="Transfer In"
        ).save()

        # Call directly, not through command line
        auto_pay_batch = Command()
        auto_pay_batch.handle()

        _test_outcome_helper(
            self.manager,
            "Sufficient funds.",
            self.manager.alan,
            self.club,
            self.membership_type.annual_fee,
            expect_stripe=False,
        )

    def test_02_auto_top_up(self):
        """User has insufficient funds to pay - use auto top up"""

        # Clear lock
        Lock.objects.all().delete()

        # Set up user
        _user_set_up_helper(
            self.manager.betty, self.club, self.membership_type, auto_top_up=True
        )

        # Not enough money in account
        MemberTransaction(
            member=self.manager.betty, amount=10, balance=0, type="Transfer In"
        ).save()

        # Call directly, not through command line
        auto_pay_batch = Command()
        auto_pay_batch.handle()

        _test_outcome_helper(
            self.manager,
            "Insufficient funds - auto top up.",
            self.manager.betty,
            self.club,
            self.membership_type.annual_fee,
            expect_stripe=True,
        )

    def test_03_insufficient_funds_no_top_up(self):
        """User has insufficient funds to pay - no auto top up"""

        # Clear lock
        Lock.objects.all().delete()

        # Set up user
        _user_set_up_helper(
            self.manager.colin, self.club, self.membership_type, auto_top_up=False
        )

        # Not enough money in account
        MemberTransaction(
            member=self.manager.colin, amount=10, balance=14.50, type="Transfer In"
        ).save()

        # Call directly, not through command line
        auto_pay_batch = Command()
        auto_pay_batch.handle()

        # Check it failed
        last_member_tran = MemberTransaction.objects.last()
        last_org_tran = OrganisationTransaction.objects.last()
        member_membership = MemberMembershipType.objects.filter(
            system_number=self.manager.colin.system_number
        ).first()

        status = not (
            last_member_tran.organisation == self.club
            or last_org_tran.member == self.manager.colin
            or member_membership.is_paid
        )

        self.manager.save_results(
            status=status,
            test_name="Auto Pay Membership batch. Insufficient funds. No auto top up",
            test_description="Test the auto_pay_memberships script",
            output=f"Last member tran org: {last_member_tran.organisation}. Last org tran: {last_org_tran.member}. Membership is Paid: {member_membership.is_paid}",
        )
