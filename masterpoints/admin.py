from django.contrib import admin

from masterpoints.models import (
    ChargeType,
    GreenPointAchievementBand,
    MasterpointEvent,
    Promotion,
    Rank,
    Period,
)

admin.site.register(ChargeType)
admin.site.register(GreenPointAchievementBand)
admin.site.register(MasterpointEvent)
admin.site.register(Promotion)
admin.site.register(Rank)
admin.site.register(Period)
