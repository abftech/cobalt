from django.contrib import admin
from django.conf.urls.static import static
from dashboard.views import logged_out, home
from django.conf import settings
from django.urls import include, path
from django_otp.admin import OTPAdminSite

from utils.views import download_csv

admin.site.site_header = f"{settings.GLOBAL_TITLE} Administration"
admin.site.site_title = f"{settings.GLOBAL_TITLE} Administration"

admin.site.add_action(download_csv, "export_as_csv")

admin.site.__class__ = OTPAdminSite

urlpatterns = [
    path("view", logged_out, name="logged_out"),
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("admin_1234567/", admin.site.urls),
    path("", home, name="home"),
    path("dashboard/", include("dashboard.urls")),
    path("results/", include("results.urls", namespace="results")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("calendar", include("calendar_app.urls", namespace="calendar")),
    path("events/", include("events.urls", namespace="events")),
    path("forums/", include("forums.urls", namespace="forums")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    path("masterpoints/", include("masterpoints.urls", namespace="masterpoints")),
    path("payments/", include("payments.urls", namespace="payments")),
    path("utils/", include("utils.urls", namespace="utils")),
    path("rbac/", include("rbac.urls", namespace="rbac")),
    path("logs/", include("logs.urls", namespace="logs")),
    path("organisations/", include("organisations.urls", namespace="organisations")),
    path("support/", include("support.urls", namespace="support")),
    path("sessions/", include("club_sessions.urls", namespace="club_sessions")),
    path("summernote/", include("django_summernote.urls")),
    path("health/", include("health_check.urls")),
    path("admin/django-ses/", include("django_ses.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Error handlers
handler404 = "cobalt.errors.not_found_404"
handler500 = "cobalt.errors.server_error_500"
handler403 = "cobalt.errors.permission_denied_403"
handler400 = "cobalt.errors.bad_request_400"
