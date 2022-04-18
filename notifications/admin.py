""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-01-24 14:43:25.002243 """

from django.contrib import admin
from .models import (
    InAppNotification,
    NotificationMapping,
    AbstractEmail,
    Email,
    EmailArchive,
    EmailThread,
    BatchID,
    Snooper,
    EmailBatchRBAC,
    BlockNotification,
    RealtimeNotificationHeader,
    RealtimeNotification,
    EmailAttachment,
)


class InAppNotificationAdmin(admin.ModelAdmin):
    """Admin class for model InAppNotification"""

    search_fields = ("member",)
    autocomplete_fields = [
        "member",
    ]


class NotificationMappingAdmin(admin.ModelAdmin):
    """Admin class for model NotificationMapping"""

    search_fields = ("member",)
    autocomplete_fields = [
        "member",
    ]


class AbstractEmailAdmin(admin.ModelAdmin):
    """Admin class for model AbstractEmail"""

    autocomplete_fields = [
        "member",
        "sender",
    ]


class SnooperAdmin(admin.ModelAdmin):
    """Admin class for model Snooper"""

    autocomplete_fields = [
        "batch_id",
    ]


class EmailBatchRBACAdmin(admin.ModelAdmin):
    """Admin class for model EmailBatchRBAC"""

    autocomplete_fields = [
        "batch_id",
        "meta_sender",
        "meta_organisation",
    ]


class BlockNotificationAdmin(admin.ModelAdmin):
    """Admin class for model BlockNotification"""

    autocomplete_fields = [
        "member",
    ]


class RealtimeNotificationHeaderAdmin(admin.ModelAdmin):
    """Admin class for model RealtimeNotificationHeader"""

    search_fields = ("admin",)
    autocomplete_fields = [
        "admin",
    ]


class RealtimeNotificationAdmin(admin.ModelAdmin):
    """Admin class for model RealtimeNotification"""

    search_fields = ("member", "admin")
    autocomplete_fields = [
        "header",
        "member",
        "admin",
    ]


class BatchIDAdmin(admin.ModelAdmin):
    """Admin class for model BatchID"""

    search_fields = ["batch_id"]


class EmailAttachmentAdmin(admin.ModelAdmin):
    """Admin class for model EmailAttachment"""

    search_fields = ("member", "organisation")
    autocomplete_fields = [
        "member",
        "organisation",
    ]


admin.site.register(InAppNotification, InAppNotificationAdmin)
admin.site.register(NotificationMapping, NotificationMappingAdmin)
admin.site.register(AbstractEmail, AbstractEmailAdmin)
admin.site.register(Email)
admin.site.register(EmailArchive)
admin.site.register(EmailThread)
admin.site.register(BatchID, BatchIDAdmin)
admin.site.register(Snooper, SnooperAdmin)
admin.site.register(EmailBatchRBAC, EmailBatchRBACAdmin)
admin.site.register(BlockNotification, BlockNotificationAdmin)
admin.site.register(RealtimeNotificationHeader, RealtimeNotificationHeaderAdmin)
admin.site.register(RealtimeNotification, RealtimeNotificationAdmin)
admin.site.register(EmailAttachment, EmailAttachmentAdmin)
