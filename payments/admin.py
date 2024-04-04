""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 12:29:48.524865 """

from django.contrib import admin
from .models import (
    StripeTransaction,
    MemberTransaction,
    OrganisationTransaction,
    StripeLog,
    PaymentStatic,
    OrganisationSettlementFees,
    OrgPaymentMethod,
    UserPendingPayment,
    MemberOrganisationLink,
)


class StripeTransactionAdmin(admin.ModelAdmin):
    """Admin class for model StripeTransaction"""

    search_fields = ["stripe_reference"]
    autocomplete_fields = [
        "member",
        "linked_organisation",
        "linked_member",
    ]


class MemberTransactionAdmin(admin.ModelAdmin):
    """Admin class for model MemberTransaction"""

    search_fields = [
        "reference_no",
        "type",
        "member__system_number",
        "member__first_name",
        "member__last_name",
    ]
    autocomplete_fields = [
        "member",
        "stripe_transaction",
        "other_member",
        "organisation",
    ]


class OrganisationTransactionAdmin(admin.ModelAdmin):
    """Admin class for model OrganisationTransaction"""

    search_fields = [
        "reference_no",
        "type",
        "organisation__name",
        "member__first_name",
        "member__last_name",
        "member__system_number",
    ]
    autocomplete_fields = [
        "organisation",
        "member",
        "stripe_transaction",
        "other_organisation",
    ]


class PaymentStaticAdmin(admin.ModelAdmin):
    """Admin class for model PaymentStatic"""

    autocomplete_fields = [
        "modified_by",
    ]


class OrgPaymentMethodAdmin(admin.ModelAdmin):
    """Admin class for model OrgPaymentMethod"""

    search_fields = ["organisation"]
    autocomplete_fields = [
        "organisation",
    ]


class UserPendingPaymentAdmin(admin.ModelAdmin):
    """Admin class for model UserPendingPayment"""

    search_fields = ["system_number", "description"]
    autocomplete_fields = [
        "organisation",
        "session_entry",
        "session_misc_payment",
    ]


class StripeLogAdmin(admin.ModelAdmin):
    search_fields = ["event"]


class MemberOrganisationLinkAdmin(admin.ModelAdmin):
    """Admin class for model MemberOrganisationLink"""

    autocomplete_fields = [
        "member_transaction",
        "organisation_transaction",
    ]


admin.site.register(StripeTransaction, StripeTransactionAdmin)
admin.site.register(MemberTransaction, MemberTransactionAdmin)
admin.site.register(OrganisationTransaction, OrganisationTransactionAdmin)
admin.site.register(StripeLog, StripeLogAdmin)
admin.site.register(PaymentStatic, PaymentStaticAdmin)
admin.site.register(OrganisationSettlementFees)
admin.site.register(OrgPaymentMethod, OrgPaymentMethodAdmin)
admin.site.register(UserPendingPayment, UserPendingPaymentAdmin)
admin.site.register(MemberOrganisationLink, MemberOrganisationLinkAdmin)
