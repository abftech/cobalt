from django.contrib import admin

from api.models import ApiLog


@admin.register(ApiLog)
class ApiLogAdmin(admin.ModelAdmin):

    autocomplete_fields = ["admin"]
