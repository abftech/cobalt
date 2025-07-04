"""Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 11:53:28.791461"""

from django.contrib import admin

from .models import (
    User,
    UnregisteredUser,
    TeamMate,
    UserPaysFor,
    APIToken,
    UserAdditionalInfo,
    SystemCard,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Controls the search fields in the Admin app"""

    search_fields = ["last_name", "first_name", "system_number", "email"]
    # We use loginas to for admins to take over a user session
    change_form_template = "loginas/change_form.html"


@admin.register(UnregisteredUser)
class UnregisteredUserAdmin(admin.ModelAdmin):
    """Admin class for model UnregisteredUser"""

    search_fields = ["last_name", "first_name", "system_number"]

    autocomplete_fields = [
        "last_updated_by",
        "last_registration_invite_by_user",
        "last_registration_invite_by_club",
        "added_by_club",
    ]


@admin.register(TeamMate)
class TeamMateAdmin(admin.ModelAdmin):
    """Admin class for model TeamMate"""

    autocomplete_fields = [
        "user",
        "team_mate",
    ]


@admin.register(UserPaysFor)
class UserPaysForAdmin(admin.ModelAdmin):
    """Admin class for model UserPaysFor"""

    autocomplete_fields = [
        "sponsor",
        "lucky_person",
    ]


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    """Admin class for model APIToken"""

    autocomplete_fields = [
        "user",
    ]


@admin.register(UserAdditionalInfo)
class UserAdditionalInfoAdmin(admin.ModelAdmin):
    """Admin class for model UserAdditionalInfo"""

    search_fields = ["user__first_name", "user__last_name", "user__system_number"]

    autocomplete_fields = [
        "user",
    ]


@admin.register(SystemCard)
class SystemCardAdmin(admin.ModelAdmin):
    """Admin class for model SystemCard"""

    autocomplete_fields = [
        "user",
    ]
