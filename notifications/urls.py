# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import path

import notifications.views.admin
import notifications.views.aws
import notifications.views.core
import notifications.views.user
from django_ses.views import SESEventWebhookView

import notifications.views.redirect

app_name = "notifications"  # pylint: disable=invalid-name

urlpatterns = [
    path(
        "ses/event-webhook/",
        SESEventWebhookView.as_view(),
        name="handle-event-webhook",
    ),
    # path(
    #     "ses/event-webhook/",
    #     notifications.views.aws.debug,
    #     name="handle-event-webhook",
    # ),
    path("", notifications.views.user.homepage, name="homepage"),
    path(
        "passthrough/<int:id>/",
        notifications.views.user.passthrough,
        name="passthrough",
    ),
    path(
        "deleteall",
        notifications.views.user.delete_all_in_app_notifications,
        name="deleteall",
    ),
    path(
        "delete/<int:id>/",
        notifications.views.user.delete_in_app_notification,
        name="delete",
    ),
    path(
        "admin/email/view-all",
        notifications.views.admin.admin_view_all_emails,
        name="admin_view_all",
    ),
    path(
        "admin/email/view-email/<int:email_id>",
        notifications.views.admin.admin_view_email,
        name="admin_view_email",
    ),
    path(
        "admin/email/view-email-by-batch/<int:batch_id>",
        notifications.views.admin.admin_view_email_by_batch,
        name="admin_view_email_by_batch",
    ),
    path(
        "admin/email/view-email-send-copy/<int:email_id>",
        notifications.views.admin.admin_send_email_copy_to_admin,
        name="admin_send_email_copy_to_admin",
    ),
    path(
        "admin/realtime/view",
        notifications.views.admin.admin_view_realtime_notifications,
        name="admin_view_realtime_notifications",
    ),
    path(
        "admin/realtime/view-details/<int:header_id>",
        notifications.views.admin.admin_view_realtime_notification_detail,
        name="admin_view_realtime_notification_detail",
    ),
    path(
        "admin/realtime/view-item/<int:notification_id>",
        notifications.views.admin.admin_view_realtime_notification_item,
        name="admin_view_realtime_notification_item",
    ),
    path(
        "admin/realtime/global-view",
        notifications.views.admin.global_admin_view_realtime_notifications,
        name="global_admin_view_realtime_notifications",
    ),
    path(
        "admin/email/view-email",
        notifications.views.admin.admin_view_email,
        name="admin_view_email",
    ),
    path(
        "email/send-email/<int:member_id>/<int:event_id>",
        notifications.views.core.email_contact,
        name="email_contact",
    ),
    path(
        "email/watch_emails/<str:batch_id>",
        notifications.views.user.watch_emails,
        name="watch_emails",
    ),
    path(
        "system-admin/player-view/<int:member_id>",
        notifications.views.admin.global_admin_view_emails,
        name="global_admin_view_emails",
    ),
    path(
        "system-admin/global-admin-view-real-time-for-user/<int:member_id>",
        notifications.views.admin.global_admin_view_real_time_for_user,
        name="global_admin_view_real_time_for_user",
    ),
    path(
        "mobile-device/send-test/<int:fcm_device_id>",
        notifications.views.core.send_test_fcm_message,
        name="send_test_fcm_message",
    ),
    path(
        "click/<str:message_id>/<str:redirect_path>",
        notifications.views.redirect.email_click_handler,
        name="email_click_handler",
    ),
    path(
        "admin-aws-suppression",
        notifications.views.aws.admin_aws_suppression,
        name="admin_aws_suppression",
    ),
    path(
        "member-to-member-email/<int:member_id>",
        notifications.views.user.member_to_member_email,
        name="member_to_member_email",
    ),
    path(
        "member-to-member-reply-to-email/<str:batch_id>",
        notifications.views.user.member_to_member_email_reply,
        name="member_to_member_email_reply",
    ),
    path(
        "admin-send-test-fcm-message",
        notifications.views.admin.admin_send_test_fcm_message,
        name="admin_send_test_fcm_message",
    ),
    path(
        "compose-email/compose-club-email/<int:club_id>",
        notifications.views.core.compose_club_email,
        name="compose_club_email",
    ),
    path(
        "initiate-email/multi-event/<int:club_id>",
        notifications.views.core.initiate_admin_multi_email,
        name="initiate_admin_multi_email",
    ),
    path(
        "compose-email/multi-event/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_multi_select,
        name="compose_email_multi_select",
    ),
    path(
        "compose-email/multi-event-by-date/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_multi_select_by_date,
        name="compose_email_multi_select_by_date",
    ),
    path(
        "compose-email/recipients/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients,
        name="compose_email_recipients",
    ),
    path(
        "compose-email/recipients-self/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_add_self,
        name="compose_email_recipients_add_self",
    ),
    path(
        "compose-email/recipients-contacts/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_add_congress_email,
        name="compose_email_recipients_add_congress_email",
    ),
    path(
        "compose-email/recipients-tadmins/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_add_tadmins,
        name="compose_email_recipients_add_tadmins",
    ),
    path(
        "compose-email/recipients-add-tags/<int:club_id>/<int:batch_id_id>/<int:tag_id>",
        notifications.views.core.compose_email_recipients_add_tag,
        name="compose_email_recipients_add_tag",
    ),
    path(
        "compose-email/recipients-add-member/<int:club_id>/<int:batch_id_id>/<int:system_number>",
        notifications.views.core.compose_email_recipients_add_member,
        name="compose_email_recipients_add_member",
    ),
    path(
        "compose-email/recipients-remove-tags/<int:club_id>/<int:batch_id_id>/<int:tag_id>/<int:from_all>",
        notifications.views.core.compose_email_recipients_remove_tag,
        name="compose_email_recipients_remove_tag",
    ),
    path(
        "compose-email/recipients-toggle-recipient/<int:recipient_id>",
        notifications.views.core.compose_email_recipients_toggle_recipient_htmx,
        name="compose_email_recipients_toggle_recipient_htmx",
    ),
    path(
        "compose-email/recipients-select-all/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_select_all,
        name="compose_email_recipients_select_all",
    ),
    path(
        "compose-email/recipients-deselect-all/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_deselect_all,
        name="compose_email_recipients_deselect_all",
    ),
    path(
        "compose-email/recipients-remove-unselected/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_remove_unselected_htmx,
        name="compose_email_recipients_remove_unselected_htmx",
    ),
    path(
        "compose-email/recipients-tags-pane-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_tags_pane_htmx,
        name="compose_email_recipients_tags_pane_htmx",
    ),
    path(
        "compose-email/recipients-member-search-pane-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_recipients_member_search_htmx,
        name="compose_email_recipients_member_search_htmx",
    ),
    path(
        "compose-email/options/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_options,
        name="compose_email_options",
    ),
    path(
        "compose-email/options-from-and-reply-to-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_options_from_and_reply_to_htmx,
        name="compose_email_options_from_and_reply_to_htmx",
    ),
    path(
        "compose-email/content/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content,
        name="compose_email_content",
    ),
    path(
        "compose-email/content/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content,
        name="compose_email_content",
    ),
    path(
        "compose-email/content-send-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content_send_htmx,
        name="compose_email_content_send_htmx",
    ),
    path(
        "compose-email/content-preview-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content_preview_htmx,
        name="compose_email_content_preview_htmx",
    ),
    path(
        "compose-email/content-attachment-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content_attachment_htmx,
        name="compose_email_content_attachment_htmx",
    ),
    path(
        "compose-email/content-upload-attachment-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content_upload_new_email_attachment_htmx,
        name="compose_email_content_upload_new_email_attachment_htmx",
    ),
    path(
        "compose-email/content-include-attachment-htmx/<int:club_id>/<int:batch_id_id>/<int:attachment_id>",
        notifications.views.core.compose_email_content_include_attachment_htmx,
        name="compose_email_content_include_attachment_htmx",
    ),
    path(
        "compose-email/content-remove-attachment-htmx/<int:club_id>/<int:batch_id_id>/<int:batch_attachment_id>",
        notifications.views.core.compose_email_content_remove_attachment_htmx,
        name="compose_email_content_remove_attachment_htmx",
    ),
    path(
        "compose-email/content-included-attachment-htmx/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.compose_email_content_included_attachments_htmx,
        name="compose_email_content_included_attachments_htmx",
    ),
    path(
        "compose-email/delete-batch/<int:club_id>/<int:batch_id_id>",
        notifications.views.core.delete_email_batch,
        name="delete_email_batch",
    ),
    path(
        "compose-email/batch-queue-progress-htmx/<int:batch_id_id>",
        notifications.views.core.batch_queue_progress_htmx,
        name="batch_queue_progress_htmx",
    ),
]
