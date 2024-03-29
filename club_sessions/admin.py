""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 12:15:50.068914 """

from django.contrib import admin

from .models import (
    SessionType,
    SessionTypePaymentMethod,
    SessionTypePaymentMethodMembership,
    Session,
    SessionEntry,
    SessionMiscPayment,
)


class SessionTypeAdmin(admin.ModelAdmin):
    """Admin class for model SessionType"""

    search_fields = ["name", "organisation"]
    autocomplete_fields = [
        "organisation",
    ]


class SessionTypePaymentMethodAdmin(admin.ModelAdmin):
    """Admin class for model SessionTypePaymentMethod"""

    search_fields = ["name", "organisation"]
    autocomplete_fields = [
        "session_type",
        "payment_method",
    ]


class SessionTypePaymentMethodMembershipAdmin(admin.ModelAdmin):
    """Admin class for model SessionTypePaymentMethodMembership"""

    search_fields = ["membership"]
    autocomplete_fields = [
        "session_type_payment_method",
        "membership",
    ]


class SessionAdmin(admin.ModelAdmin):
    """Admin class for model Session"""

    search_fields = ["director", "venue"]
    autocomplete_fields = [
        "director",
        "session_type",
        "venue",
    ]


class SessionEntryAdmin(admin.ModelAdmin):
    """Admin class for model SessionEntry"""

    search_fields = ["player"]
    autocomplete_fields = [
        "session",
        "org_tran",
        "member_tran",
        "payment_method",
    ]


class MemberOrganisationLinkAdmin(admin.ModelAdmin):
    """Admin class for model MemberOrganisationLink"""

    autocomplete_fields = [
        "member_transaction",
        "organisation_transaction",
    ]


class SessionMiscPaymentAdmin(admin.ModelAdmin):
    """Admin class for model SessionMiscPayment"""

    search_fields = ["system_number"]

    autocomplete_fields = [
        "session_entry",
    ]


admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(SessionTypePaymentMethod, SessionTypePaymentMethodAdmin)
admin.site.register(
    SessionTypePaymentMethodMembership, SessionTypePaymentMethodMembershipAdmin
)
admin.site.register(Session, SessionAdmin)
admin.site.register(SessionEntry, SessionEntryAdmin)
admin.site.register(SessionMiscPayment, SessionMiscPaymentAdmin)
