""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 11:53:28.791461 """

from django.contrib import admin
from .models import (
    User,
    UnregisteredUser,
    TeamMate,
    UserPaysFor,
    APIToken,
    UserAdditionalInfo,
)


class UserAdmin(admin.ModelAdmin):
    """Controls the search fields in the Admin app"""

    search_fields = ["last_name", "first_name", "system_number", "email"]
    # We use loginas to for admins to take over a user session
    change_form_template = "loginas/change_form.html"


class UnregisteredUserAdmin(admin.ModelAdmin):
    """Admin class for model UnregisteredUser"""

    autocomplete_fields = [
        "last_updated_by",
        "last_registration_invite_by_user",
        "last_registration_invite_by_club",
        "added_by_club",
    ]


class TeamMateAdmin(admin.ModelAdmin):
    """Admin class for model TeamMate"""

    autocomplete_fields = [
        "user",
        "team_mate",
    ]


class UserPaysForAdmin(admin.ModelAdmin):
    """Admin class for model UserPaysFor"""

    autocomplete_fields = [
        "sponsor",
        "lucky_person",
    ]


class APITokenAdmin(admin.ModelAdmin):
    """Admin class for model APIToken"""

    autocomplete_fields = [
        "user",
    ]


class UserAdditionalInfoAdmin(admin.ModelAdmin):
    """Admin class for model UserAdditionalInfo"""

    autocomplete_fields = [
        "user",
    ]


admin.site.register(User, UserAdmin)
admin.site.register(UnregisteredUser, UnregisteredUserAdmin)
admin.site.register(TeamMate, TeamMateAdmin)
admin.site.register(UserPaysFor, UserPaysForAdmin)
admin.site.register(APIToken, APITokenAdmin)
admin.site.register(UserAdditionalInfo, UserAdditionalInfoAdmin)
