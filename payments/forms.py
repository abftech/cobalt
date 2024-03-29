""" Payment forms with validation """

from django import forms
from accounts.models import User
from organisations.models import Organisation
from cobalt.settings import (
    AUTO_TOP_UP_MIN_AMT,
    AUTO_TOP_UP_MAX_AMT,
    GLOBAL_CURRENCY_SYMBOL,
)
from .models import (
    TRANSACTION_TYPE,
    MemberTransaction,
    OrganisationTransaction,
    PaymentStatic,
    OrganisationSettlementFees,
)
from django.core.exceptions import ValidationError


# class TestTransaction(forms.Form):
#     """ Temporary - will be removed """
#
#     amount = forms.DecimalField(label="Amount", max_digits=8, decimal_places=2)
#     description = forms.CharField(label="Description", max_length=100)
#     organisation = forms.ModelChoiceField(queryset=Organisation.objects.all())
#     type = forms.ChoiceField(label="Transaction Type", choices=TRANSACTION_TYPE)
#     url = forms.CharField(label="URL", max_length=100, required=False)


class MemberTransfer(forms.Form):
    """M2M transfer form"""

    transfer_to = forms.ModelChoiceField(queryset=User.objects.all())
    amount = forms.DecimalField(label="Amount", max_digits=8, decimal_places=2)
    description = forms.CharField(label="Description", max_length=80)

    # We need the logged in user to check the balance, add a parameter
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)


class MemberTransferOrg(forms.Form):
    """Org to Member transfer form"""

    transfer_to = forms.ModelChoiceField(queryset=User.objects.all())
    amount = forms.DecimalField(label="Amount", max_digits=8, decimal_places=2)
    description = forms.CharField(label="Description", max_length=80)

    # We need the balance to take it as a parameter
    def __init__(self, *args, **kwargs):
        self.balance = kwargs.pop("balance", 0.0)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        """check the balance is sufficient for the payment"""

        amount = self.cleaned_data["amount"]
        if amount > self.balance:
            raise ValidationError("Insufficient funds")
        return amount


class ManualTopup(forms.Form):
    """Manual top up form"""

    CARD_CHOICES = [
        ("Existing", "Use Registered Card"),
        ("Another", "Use Another Card"),
    ]

    amount = forms.DecimalField(label="Amount", max_digits=8, decimal_places=2)
    card_choice = forms.ChoiceField(
        label="Card Option", choices=CARD_CHOICES, required=False
    )

    # We need the balance to take it as a parameter
    def __init__(self, *args, **kwargs):
        self.balance = kwargs.pop("balance", 0.0)
        super().__init__(*args, **kwargs)

    def clean(self):
        """validation for the amount field"""
        cleaned_data = super(ManualTopup, self).clean()
        if cleaned_data.get("amount"):
            amount = self.cleaned_data["amount"]
            if amount < AUTO_TOP_UP_MIN_AMT:
                txt = "Insufficient amount. Minimum is %s%s" % (
                    GLOBAL_CURRENCY_SYMBOL,
                    AUTO_TOP_UP_MIN_AMT,
                )
                self._errors["amount"] = txt
                raise forms.ValidationError(txt)
            if amount > AUTO_TOP_UP_MAX_AMT - self.balance:

                txt = "Too large. Maximum balance is %s%s" % (
                    GLOBAL_CURRENCY_SYMBOL,
                    AUTO_TOP_UP_MAX_AMT,
                )
                self._errors["amount"] = txt
                raise forms.ValidationError(txt)
        else:
            self._errors["amount"] = "Please enter a value"

        return self.cleaned_data


class SettlementForm(forms.Form):
    """For payments to Orgs"""

    CARD_CHOICES = [
        ("Dummy", "Dummy"),
    ]

    # Handle checkboxes
    settle_list = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=CARD_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        """dynamic override of checkbox list"""

        # Get list of orgs
        self.orgs = kwargs.pop("orgs", None)
        super().__init__(*args, **kwargs)
        self.fields["settle_list"].choices = self.orgs


class AdjustMemberForm(forms.ModelForm):
    """For dodgy changes to members"""

    class Meta:
        model = MemberTransaction
        fields = (
            "member",
            "description",
            "amount",
        )


class AdjustOrgForm(forms.ModelForm):
    """For dodgy changes to orgs"""

    adjustment_type = forms.ChoiceField(
        choices=[(1, "Manual Adjustment"), (2, "Settlement")]
    )

    class Meta:
        model = OrganisationTransaction
        fields = (
            "organisation",
            "description",
            "amount",
        )

    def __init__(self, *args, **kwargs):
        """dynamic set of default value on dropdown"""

        # Get default value
        default_transaction = kwargs.pop("default_transaction", None)
        super().__init__(*args, **kwargs)
        self.fields["adjustment_type"].initial = default_transaction

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        adjustment_type = cleaned_data.get("adjustment_type")
        if adjustment_type == "2" and amount >= 0:
            self.add_error("amount", "Settlement amount must be negative")
        return cleaned_data


class DateForm(forms.Form):
    """for simple from to date ranges"""

    from_date = forms.DateField(input_formats=["%d/%m/%Y"])
    to_date = forms.DateField(input_formats=["%d/%m/%Y"])


class PaymentStaticForm(forms.ModelForm):
    """static data on payments"""

    class Meta:
        model = PaymentStatic
        fields = (
            "default_org_fee_percent",
            "stripe_cost_per_transaction",
            "stripe_percentage_charge",
            "stripe_refund_percentage_charge",
            "stripe_refund_weeks",
        )


class OrgStaticOverrideForm(forms.ModelForm):
    """override default ABF fees for an organisation"""

    class Meta:
        model = OrganisationSettlementFees
        fields = ("organisation", "org_fee_percent")


class StripeRefund(forms.Form):
    """Allow admins to make Stripe refunds"""

    amount = forms.DecimalField(label="Refund", max_digits=8, decimal_places=2)
    description = forms.CharField(max_length=80)

    def __init__(self, *args, **kwargs):
        self.payment_amount = kwargs.pop("payment_amount", 0.0)
        super().__init__(*args, **kwargs)

    def clean(self):
        """validation for the amount field"""
        cleaned_data = super(StripeRefund, self).clean()
        if cleaned_data.get("amount"):
            amount = self.cleaned_data["amount"]
            if amount < 0.0:
                raise forms.ValidationError("Amount cannot be negative")
            if amount > self.payment_amount:
                raise forms.ValidationError("Too large. Refund is more than was paid.")
        else:
            raise forms.ValidationError("Please enter a value")

        return self.cleaned_data
