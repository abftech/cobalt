# -*- coding: utf-8 -*-
"""Model definitions for Payments.

See `Payments Overview`_ for more details.

.. _Payments Overview:
   ./payments_overview.html

"""

import random
import string
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import User
from organisations.models import Organisation
from cobalt.settings import GLOBAL_CURRENCY_SYMBOL, GLOBAL_ORG

TRANSACTION_TYPE = [
    ("Transfer Out", "Money transferred out of account"),
    ("Transfer In", "Money transferred in to account"),
    ("Auto Top Up", "Automated CC top up"),
    ("Manual Top Up", "Manual CC top up"),
    ("Club Top Up", "Club top up"),
    ("Club Top Up Rev", "Club top up reversal"),
    ("Entry to an event", "Entry to an event"),
    ("CC Payment", "Credit Card payment"),
    ("Club Payment", "Club game payment"),
    ("Club Top Up", "Club Top Up"),
    ("Club Membership", "Club membership payment"),
    ("Member Transfer", "Payment to another member"),
    ("Miscellaneous", "Miscellaneous payment"),
    ("Settlement", "Settlement payment"),
    ("Manual Adjustment", "Manual adjustment"),
    ("Org Transfer", "Organisation Transfer"),
    # Refund is Org to Player +ve for player
    ("Refund", "Refund"),
    # Card Refund is ABF to Players Credit Card -ve for player
    ("Card Refund", "Refund to a card"),
]


class TransactionType(models.TextChoices):
    CONGRESS = "CO"
    SESSION = "SE"


class StripeTransaction(models.Model):
    """Our record of Stripe transactions.

    Only stores basic information, for the full details use the
    stripe_reference to look up the transaction in Stripe.

    """

    TRANSACTION_STATUS = [
        # This is the default status
        ("Initiated", "Initiated - Stripe Transaction object created"),
        # This means we have hit the checkout page and Stripe is waiting
        ("Intent", "Intent - received customer intent to pay from Stripe"),
        # This means they have been confirmed with strip, but we haven't been notified yet
        # Note - this is notified by client side code and cannot be trusted
        ("Pending", "Pending - transaction approved by Stripe - awaiting confirmation"),
        # This means it worked and we have their cash
        ("Succeeded", "Succeeded - payment completed successfully"),
        # This means we didn't get their cash - although currently nothing gets set to failed
        ("Failed", "Failed - payment failed"),
        # Refund statuses - matches Stripe
        ("Partial refund", "Partial refund - some money returned"),
        ("Refunded", "Refunded - Fully refunded"),
    ]

    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="User object associated with this transaction",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="main_member",
    )
    """ Link to the member(User object) that is associated with this transaction."""

    description = models.TextField("Description")
    """ Description of the transaction."""

    amount = models.DecimalField("Amount", max_digits=8, decimal_places=2)
    """ Amount of the transaction in currency unit (default Australian Dollars).
    Be careful as Stripe stores the amount in cents, not dollars."""

    status = models.CharField(
        "Status", max_length=20, choices=TRANSACTION_STATUS, default="Initiated"
    )
    """ Status of the transaction. See TRANSACTION_STATUS for options."""

    stripe_reference = models.CharField(
        "Stripe Payment Intent", blank=True, null=True, max_length=40
    )
    """ Reference passed by Stripe. Use this to look up more detail within
    Stripe itself."""

    stripe_method = models.CharField(
        "Stripe Payment Method", blank=True, null=True, max_length=40
    )
    """Stripe payment method - always "Card"."""

    stripe_currency = models.CharField(
        "Card Native Currency", blank=True, null=True, max_length=3
    )
    """Stripe currency for the transaction."""

    stripe_receipt_url = models.CharField(
        "Receipt URL", blank=True, null=True, max_length=200
    )
    """Stripe receipt URL. User can go directly to this for Stripe info."""

    stripe_balance_transaction = models.CharField(
        "Stripe Balance Transaction", blank=True, null=True, max_length=200
    )

    stripe_brand = models.CharField("Card brand", blank=True, null=True, max_length=10)

    stripe_country = models.CharField(
        "Card Country", blank=True, null=True, max_length=5
    )

    stripe_exp_month = models.IntegerField("Card Expiry Month", blank=True, null=True)

    stripe_exp_year = models.IntegerField("Card Expiry Year", blank=True, null=True)

    stripe_last4 = models.CharField(
        "Card Last 4 Digits", blank=True, null=True, max_length=4
    )
    route_code = models.CharField(
        "Internal routing code for callback", blank=True, null=True, max_length=4
    )

    route_payload = models.CharField(
        "Payload to return to callback", blank=True, null=True, max_length=40
    )

    created_date = models.DateTimeField("Creation Date", default=timezone.now)

    last_change_date = models.DateTimeField("Last Update Date", default=timezone.now)

    linked_organisation = models.ForeignKey(
        Organisation, blank=True, null=True, on_delete=models.SET_NULL
    )
    """ A stripe payment can be linked to a payment to an organisation or
    to a member, but not both """

    linked_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="linked_member",
    )
    """ A stripe payment can be linked to a payment to an organisation or
    to a member, but not both """

    linked_transaction_type = models.CharField(
        "Linked Transaction Type", blank=True, null=True, max_length=20
    )
    """ Type of the transaction that we are linked to. This is payload on
    StripeTransaction that is used to create the linked MemberTransaction or
    OrganisationTransaction record."""

    linked_amount = models.DecimalField(
        "Linked Amount", blank=True, null=True, max_digits=12, decimal_places=2
    )
    """linked amount can be different to amount if the member had some money in their account already"""

    refund_amount = models.DecimalField(
        "Refund Amount", default=0.0, max_digits=12, decimal_places=2
    )
    """How much has been refunded"""

    def __str__(self):
        return "%s(%s %s) - %s" % (
            self.member.system_number,
            self.member.first_name,
            self.member.last_name,
            self.stripe_reference,
        )


class AbstractTransaction(models.Model):
    """Common attributes for the other transaction classes"""

    created_date = models.DateTimeField("Create Date", default=timezone.now)

    amount = models.DecimalField("Amount", max_digits=12, decimal_places=2)

    balance = models.DecimalField(
        "Balance After Transaction", max_digits=12, decimal_places=2
    )

    description = models.TextField("Transaction Description", blank=True, null=True)

    reference_no = models.CharField(
        "Reference No", max_length=14, blank=True, null=True
    )

    type = models.CharField("Transaction Type", choices=TRANSACTION_TYPE, max_length=20)

    # Sessions are important enough to Organisations that we add them here. Lets us summarise by session
    # We can't use a foreign key as there is a circular import issue
    club_session_id = models.IntegerField(blank=True, null=True)

    # Event id is needed for summarising by event
    event_id = models.IntegerField(blank=True, null=True)

    #    session = models.ForeignKey(Session, blank=True, null=True, on_delete=models.PROTECT)

    class Meta:  # pylint: disable=too-few-public-methods,missing-class-docstring
        abstract = True


class MemberTransaction(AbstractTransaction):
    """Member Transactions. May have a linked transaction."""

    # This is the primary member whose account is being interacted with
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        #        null=True,
        on_delete=models.PROTECT,
        related_name="primary_member",
    )

    # Each record with have one of the following 3 things
    # This is linked to a stripe transaction, so from our point of view this is money in
    stripe_transaction = models.ForeignKey(
        StripeTransaction, blank=True, null=True, on_delete=models.PROTECT
    )
    # It is linked to another member, so internal transfer to or from this member
    # This will not have a stripe_transaction or an organisation set
    other_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="other_member",
    )
    # It is linked to an organisation so usually a payment to a club or congress
    # for entry fees or subscriptions.
    # Could also be a payment from the organisation for a refund for example.
    # Can have a stripe_transaction as well
    organisation = models.ForeignKey(
        Organisation, blank=True, null=True, on_delete=models.PROTECT
    )

    def save(self, *args, **kwargs):
        if self.description:
            self.description = self.description[:80]
        if not self.reference_no:
            self.reference_no = "%s-%s-%s" % (
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4)),
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4)),
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            )
        super(MemberTransaction, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.member} - {self.type}"


class OrganisationTransaction(AbstractTransaction):
    """Organisation transactions."""

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        related_name="primary_org",
    )
    # Organisation can have one and only one of the 3 following things
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.PROTECT
    )

    stripe_transaction = models.ForeignKey(
        StripeTransaction, blank=True, null=True, on_delete=models.PROTECT
    )

    other_organisation = models.ForeignKey(
        Organisation,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="secondary_org",
    )

    bank_settlement_amount = models.DecimalField(
        "Bank Settlement Amount", max_digits=12, decimal_places=2, null=True, blank=True
    )
    """ Records the actual amount paid out minus the fees for settlement transactions. Blank for anything else"""

    def save(self, *args, **kwargs):
        if not self.reference_no:
            self.reference_no = "%s-%s-%s" % (
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4)),
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4)),
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            )
        super(OrganisationTransaction, self).save(*args, **kwargs)

    @property
    def settlement_amount(self):
        """How much will org actually be paid for this BALANCE (not amount) after we deduct our fees

        We include the organisations minimum balance after settlement in the calculation so that
        we leave a float in the club's account to take care of any outgoings before payments come in

        """

        # Calculate the fee percentage. e.g. if the ABF charge this club 5%, this will be 0.95
        percent = 1.0 - (float(self.organisation.settlement_fee_percent) / 100.0)

        # Include balance after settlement
        gross_amount = float(self.balance) - float(
            self.organisation.minimum_balance_after_settlement
        )
        gross_amount = max(gross_amount, 0)

        # Calculate settlement amount
        settlement_value = gross_amount * percent

        return round(settlement_value, 2)

    def __str__(self):
        return f"{self.organisation.name} - {self.id}"


class StripeLog(models.Model):
    """Log messages received from Stripe on the webhook in case we need them in full"""

    created_date = models.DateTimeField("Create Date", default=timezone.now)
    event = models.TextField("Event", blank=True, null=True)
    event_type = models.TextField("Event Type", blank=True, null=True)
    cobalt_tran_type = models.TextField("Cobalt Tran Type", blank=True, null=True)

    def __str__(self):
        return f"{self.event_type} - {self.created_date}"


class PaymentStatic(models.Model):
    """single row table with static data on payments"""

    active = models.BooleanField("Active", default=True)
    created_date = models.DateTimeField("Create Date", default=timezone.now)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )
    # default fee to charge orgs when making a settlement
    default_org_fee_percent = models.DecimalField(
        f"{GLOBAL_ORG} Settlement Fee Percent for Organisations (default)",
        max_digits=8,
        decimal_places=2,
    )
    stripe_cost_per_transaction = models.DecimalField(
        f"Stripe Fee Per Transaction {GLOBAL_CURRENCY_SYMBOL}",
        max_digits=8,
        decimal_places=4,
    )
    stripe_percentage_charge = models.DecimalField(
        "Stripe Fee Percentage (per transaction)", max_digits=8, decimal_places=4
    )
    stripe_refund_percentage_charge = models.DecimalField(
        "Percentage to charge members for refunds",
        max_digits=8,
        decimal_places=4,
        default=3.0,
    )
    stripe_refund_weeks = models.IntegerField(
        "Number of weeks ago to allow refund", default=12
    )

    def __str__(self):
        return f"{self.active} - {self.created_date}"


class OrganisationSettlementFees(models.Model):
    """ability to override default_org_fee_percent for an organisation"""

    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE)
    org_fee_percent = models.DecimalField(
        "Organisation Settlement Fee Percent", max_digits=8, decimal_places=2
    )

    class Meta:
        verbose_name_plural = "organisation settlement fees"

    def __str__(self):
        return f"{self.organisation} - {self.org_fee_percent}"


class OrgPaymentMethod(models.Model):
    """Defines the types of payments that an organisation will accept
    These are Bridge Credits plus any kind of off system payment. We allow an organisation
    to enter anything they like here but create sensible defaults for them.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=15)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["organisation", "payment_method"]

    def __str__(self):
        return f"{self.organisation} - {self.payment_method}"


class UserPendingPayment(models.Model):
    """This is basically an IOU for when a player cannot pay for something at a club
    but the club is okay for them to pay later."""

    from club_sessions.models import SessionEntry, SessionMiscPayment

    system_number = models.IntegerField(f"{GLOBAL_ORG} Number")
    """ We use system_number to cover both Users and UnregisteredUsers """
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    session_entry = models.ForeignKey(
        SessionEntry, on_delete=models.CASCADE, blank=True, null=True
    )
    """ Optional but likely that this IOU is for a session that they played in"""
    session_misc_payment = models.ForeignKey(
        SessionMiscPayment, on_delete=models.CASCADE, blank=True, null=True
    )
    """ Optional For a miscellaneous payment we want the id of the payment, not just the session id"""

    def __str__(self):
        return f"{self.system_number} - {GLOBAL_CURRENCY_SYMBOL}{self.amount:,.2f} - {self.description}"


class MemberOrganisationLink(models.Model):
    """This was built to provide the linkage between users, clubs and general, small payments. However,
    it can be used any time you want to link a specific member_transaction to a specific organisation_transaction.
    These link to a user or an org, but you won't know which specific transaction without this linkage.

    We could have solved this by adding an optional field to MemberTransaction and OrganisationTransaction
    but they are already overloaded. Another option would have been to add a metaclass to both with
    extended data. This looks like the most generic solution, however.

    """

    member_transaction = models.ForeignKey(MemberTransaction, on_delete=models.CASCADE)
    organisation_transaction = models.ForeignKey(
        OrganisationTransaction, on_delete=models.CASCADE
    )
