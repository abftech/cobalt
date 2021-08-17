# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import path
from . import views
from django_ses.views import SESEventWebhookView
from django.views.decorators.csrf import csrf_exempt

app_name = "notifications"  # pylint: disable=invalid-name

urlpatterns = [
    path(
        "ses/event-webhook/", SESEventWebhookView.as_view(), name="handle-event-webhook"
    ),
    path("", views.homepage, name="homepage"),
    path("passthrough/<int:id>/", views.passthrough, name="passthrough"),
    path("deleteall", views.deleteall, name="deleteall"),
    path("delete/<int:id>/", views.delete, name="delete"),
    path("admin/view-all", views.admin_view_all, name="admin_view_all"),
    path(
        "admin/view-email/<int:email_id>",
        views.admin_view_email,
        name="admin_view_email",
    ),
    path("admin/view-email", views.admin_view_email, name="admin_view_email"),
    path("email/send-email/<int:member_id>", views.email_contact, name="email_contact"),
    path("email/watch_emails/<str:batch_id>", views.watch_emails, name="watch_emails"),
]
