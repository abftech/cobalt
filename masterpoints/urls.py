from django.urls import path
from . import views

app_name = "masterpoints"  # pylint: disable=invalid-name

urlpatterns = [
    path("", views.masterpoints_detail_html, name="masterpoints"),
    path("<int:years>/", views.masterpoints_detail_html, name="masterpoints_years"),
    path(
        "view/<int:system_number>/",
        views.masterpoints_detail_html,
        name="masterpoints_detail",
    ),
    path(
        "view/<int:system_number>/<int:years>/",
        views.masterpoints_detail_html,
        name="masterpoints_detail_years",
    ),
    path(
        "system_number_lookup", views.system_number_lookup, name="system_number_lookup"
    ),
    path("masterpoints_search", views.masterpoints_search, name="masterpoints_search"),
    path("abf-card-pdf", views.download_abf_card_pdf, name="abf_card"),
    path(
        "abf-registration-card",
        views.abf_registration_card,
        name="abf_registration_card",
    ),
    path(
        "abf-registration-card-htmx",
        views.abf_registration_card_htmx,
        name="abf_registration_card_htmx",
    ),
]
