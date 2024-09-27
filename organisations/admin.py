""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 14:54:06.307431 """

from django.contrib import admin
from .models import (
    Organisation,
    MembershipType,
    MemberMembershipType,
    ClubLog,
    MemberClubEmail,
    ClubTag,
    MemberClubTag,
    Visitor,
    OrganisationFrontPage,
    MiscPayType,
    OrgVenue,
    WelcomePack,
    OrgEmailTemplate,
    MemberClubDetails,
    MemberClubOptions,
    ClubMemberLog,
)


class OrganisationAdmin(admin.ModelAdmin):
    """Admin class for model Organisation"""

    autocomplete_fields = [
        "secretary",
        "last_updated_by",
    ]
    search_fields = ["name"]


class MembershipTypeAdmin(admin.ModelAdmin):
    """Admin class for model MembershipType"""

    search_fields = [
        "organisation",
        "last_modified_by",
    ]
    autocomplete_fields = [
        "organisation",
        "last_modified_by",
    ]


class MemberMembershipTypeAdmin(admin.ModelAdmin):
    """Admin class for model MemberMembershipType"""

    autocomplete_fields = [
        "membership_type",
        "last_modified_by",
    ]

    search_fields = ["system_number"]


class ClubLogAdmin(admin.ModelAdmin):
    """Admin class for model ClubLog"""

    autocomplete_fields = [
        "organisation",
        "actor",
    ]


class MemberClubEmailAdmin(admin.ModelAdmin):
    """Admin class for model MemberClubEmail"""

    autocomplete_fields = [
        "organisation",
    ]

    search_fields = [
        "email",
    ]


class ClubTagAdmin(admin.ModelAdmin):
    """Admin class for model ClubTag"""

    search_fields = [
        "organisation",
    ]
    autocomplete_fields = [
        "organisation",
    ]


class MemberClubTagAdmin(admin.ModelAdmin):
    """Admin class for model MemberClubTag"""

    autocomplete_fields = [
        "club_tag",
    ]


class VisitorAdmin(admin.ModelAdmin):
    """Admin class for model Visitor"""

    autocomplete_fields = [
        "organisation",
    ]


class MiscPayTypeAdmin(admin.ModelAdmin):
    """Admin class for model MiscPayType"""

    autocomplete_fields = [
        "organisation",
    ]


class OrgVenueAdmin(admin.ModelAdmin):
    """Admin class for model OrgVenue"""

    search_fields = [
        "organisation",
    ]

    autocomplete_fields = [
        "organisation",
    ]


class WelcomePackAdmin(admin.ModelAdmin):
    """Admin class for model WelcomePack"""

    search_fields = [
        "organisation",
        "template",
    ]

    autocomplete_fields = [
        "organisation",
        "template",
        "last_modified_by",
    ]


class OrgEmailTemplateAdmin(admin.ModelAdmin):
    """Admin class for model OrgEmailTemplate"""

    search_fields = [
        "organisation",
    ]

    autocomplete_fields = [
        "organisation",
        "last_modified_by",
    ]


class MemberClubDetailsAdmin(admin.ModelAdmin):
    """Admin class for model MemberClubDetails"""

    search_fields = [
        "club__name",
        "system_number",
        "email",
    ]

    autocomplete_fields = [
        "club",
    ]


class MemberClubOptionsAdmin(admin.ModelAdmin):
    """Admin class for model MemberClubOptions"""

    search_fields = [
        "club__name",
        "user__last_name",
        "user__first_name",
    ]

    autocomplete_fields = [
        "club",
    ]


class ClubMemberLogAdmin(admin.ModelAdmin):
    """Admin class for model ClubMemberLog"""

    search_fields = [
        "club__name",
        "system_number",
    ]

    autocomplete_fields = [
        "club",
    ]


admin.site.register(Organisation, OrganisationAdmin)
admin.site.register(OrgEmailTemplate, OrgEmailTemplateAdmin)
admin.site.register(MembershipType, MembershipTypeAdmin)
admin.site.register(MemberMembershipType, MemberMembershipTypeAdmin)
admin.site.register(MemberClubDetails, MemberClubDetailsAdmin)
admin.site.register(MemberClubOptions, MemberClubOptionsAdmin)
admin.site.register(ClubMemberLog, ClubMemberLogAdmin)
admin.site.register(ClubLog, ClubLogAdmin)
admin.site.register(MemberClubEmail, MemberClubEmailAdmin)
admin.site.register(ClubTag, ClubTagAdmin)
admin.site.register(MemberClubTag, MemberClubTagAdmin)
admin.site.register(Visitor, VisitorAdmin)
admin.site.register(OrganisationFrontPage)
admin.site.register(MiscPayType, MiscPayTypeAdmin)
admin.site.register(OrgVenue, OrgVenueAdmin)
admin.site.register(WelcomePack, WelcomePackAdmin)
