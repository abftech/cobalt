""" Generated by utils/cgit/cgit_util_generate_admin_file on 2022-05-03 08:32:37.897641 """

from django.contrib import admin
from .models import ResultsFile, PlayerSummaryResult


class ResultsFileAdmin(admin.ModelAdmin):
    """Admin class for model ResultsFile"""

    search_fields = ("results_file",)

    autocomplete_fields = [
        "uploaded_by",
        "organisation",
    ]


class PlayerSummaryResultAdmin(admin.ModelAdmin):
    """Admin class for model PlayerSummaryResult"""

    autocomplete_fields = [
        "results_file",
    ]


admin.site.register(ResultsFile, ResultsFileAdmin)
admin.site.register(PlayerSummaryResult, PlayerSummaryResultAdmin)
