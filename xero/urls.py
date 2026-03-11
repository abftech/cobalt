from django.urls import path
from . import views

app_name = "xero"

urlpatterns = [
    path("", views.home, name="xero_home"),
    path("connect", views.connect_htmx, name="xero_connect_htmx"),
    path("config", views.home_configuration_htmx, name="xero_home_config_htmx"),
    path("refresh", views.refresh_keys_htmx, name="xero_refresh_keys_htmx"),
    path("run-xero-api", views.run_xero_api_htmx, name="run_xero_api_htmx"),
    path("invoice-form", views.invoice_form_htmx, name="invoice_form_htmx"),
    path("webhook", views.xero_webhook, name="xero_webhook"),
]
