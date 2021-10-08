from django.contrib import admin

from club_sessions.models import (
    Session,
    SessionType,
    SessionTypePaymentMethod,
    SessionEntry,
)

admin.site.register(Session)
admin.site.register(SessionType)
admin.site.register(SessionTypePaymentMethod)
admin.site.register(SessionEntry)
