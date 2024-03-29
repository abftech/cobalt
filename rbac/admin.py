""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 14:56:11.114685 """

from django.contrib import admin
from .models import (
    RBACGroup,
    RBACUserGroup,
    RBACGroupRole,
    RBACModelDefault,
    RBACAppModelAction,
    RBACAdminGroup,
    RBACAdminUserGroup,
    RBACAdminGroupRole,
    RBACAdminTree,
)


class RBACGroupAdmin(admin.ModelAdmin):
    """Admin class for model RBACGroup"""

    list_display = ["name", "name_qualifier", "name_item", "description"]
    search_fields = ["name_qualifier", "name_item", "description"]
    autocomplete_fields = [
        "created_by",
    ]


class RBACUserGroupAdmin(admin.ModelAdmin):
    """Admin class for model RBACUserGroup"""

    autocomplete_fields = [
        "member",
        "group",
    ]
    list_display = ["group", "member"]
    search_fields = [
        "group__description",
        "group__name_qualifier",
        "group__name_item",
        "member__first_name",
        "member__last_name",
    ]


class RBACGroupRoleAdmin(admin.ModelAdmin):
    """Admin class for model RBACGroupRole"""

    autocomplete_fields = [
        "group",
    ]
    list_display = [
        "group",
        "role",
        "action",
        "rule_type",
    ]
    search_fields = [
        "group__name",
        "role",
    ]


class RBACAdminGroupAdmin(admin.ModelAdmin):
    """Admin class for model RBACAdminGroup"""

    autocomplete_fields = [
        "created_by",
    ]
    list_display = ["name", "name_qualifier", "name_item", "description"]
    search_fields = ["name_qualifier", "name_item", "description"]


class RBACAdminUserGroupAdmin(admin.ModelAdmin):
    """Admin class for model RBACAdminUserGroup"""

    autocomplete_fields = [
        "member",
        "group",
    ]
    list_display = ["group", "member"]
    search_fields = [
        "group__description",
        "group__name_qualifier",
        "group__name_item",
        "member__first_name",
        "member__last_name",
    ]


class RBACAdminGroupRoleAdmin(admin.ModelAdmin):
    """Admin class for model RBACAdminGroupRole"""

    autocomplete_fields = [
        "group",
    ]
    list_display = [
        "group",
        "app",
        "model",
        "model_id",
    ]
    search_fields = [
        "group__name_item",
        "app",
    ]


class RBACAdminTreeAdmin(admin.ModelAdmin):
    """Admin class for model RBACAdminTree"""

    autocomplete_fields = [
        "group",
    ]
    list_display = ["group", "tree"]
    search_fields = [
        "group__description",
        "group__name_qualifier",
        "group__name_item",
        "tree",
    ]


class RBACModelDefaultAdmin(admin.ModelAdmin):
    list_display = [
        "app",
        "model",
        "default_behaviour",
    ]
    search_fields = ["app", "model", "default_behaviour"]


class RBACAppModelActionAdmin(admin.ModelAdmin):
    list_display = [
        "app",
        "model",
        "valid_action",
        "description",
    ]
    search_fields = [
        "app",
        "model",
        "valid_action",
        "description",
    ]


admin.site.register(RBACGroup, RBACGroupAdmin)
admin.site.register(RBACUserGroup, RBACUserGroupAdmin)
admin.site.register(RBACGroupRole, RBACGroupRoleAdmin)
admin.site.register(RBACModelDefault, RBACModelDefaultAdmin)
admin.site.register(RBACAppModelAction, RBACAppModelActionAdmin)
admin.site.register(RBACAdminGroup, RBACAdminGroupAdmin)
admin.site.register(RBACAdminUserGroup, RBACAdminUserGroupAdmin)
admin.site.register(RBACAdminGroupRole, RBACAdminGroupRoleAdmin)
admin.site.register(RBACAdminTree, RBACAdminTreeAdmin)
