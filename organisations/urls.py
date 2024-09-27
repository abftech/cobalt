# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import path

import organisations.views.club_menu
import organisations.views.club_menu_tabs.access
import organisations.views.club_menu_tabs.comms
import organisations.views.club_menu_tabs.congresses
import organisations.views.club_menu_tabs.dashboard
import organisations.views.club_menu_tabs.finance
import organisations.views.club_menu_tabs.import_data
import organisations.views.club_menu_tabs.members
import organisations.views.club_menu_tabs.contacts
import organisations.views.club_menu_tabs.results
import organisations.views.club_menu_tabs.sessions
import organisations.views.club_menu_tabs.settings
import organisations.views.club_menu_tabs.utils
import organisations.views.home
import organisations.views.club_admin
from .views import club_menu, ajax

from .views import admin
from .views import general

app_name = "organisations"  # pylint: disable=invalid-name

urlpatterns = [
    path("general", organisations.views.home.home, name="home"),
    path("org-search-ajax", ajax.org_search_ajax, name="org_search_ajax"),
    path("org-detail-ajax", ajax.org_detail_ajax, name="org_detail_ajax"),
    path(
        "admin/club-details", ajax.get_club_details_htmx, name="get_club_details_ajax"
    ),
    path(
        "admin/club-name-search",
        ajax.club_name_search_htmx,
        name="club_name_search_ajax",
    ),
    path("edit/<int:org_id>", general.org_edit, name="org_edit"),
    path(
        "admin/add-club",
        admin.admin_add_club,
        name="admin_add_club",
    ),
    path(
        "admin/list-clubs",
        admin.admin_list_clubs,
        name="admin_list_clubs",
    ),
    path(
        "admin/club-rbac/<int:club_id>",
        admin.admin_club_rbac,
        name="admin_club_rbac",
    ),
    path(
        "admin/club-rbac-basic/<int:club_id>",
        admin.admin_club_rbac_add_basic,
        name="admin_club_rbac_add_basic",
    ),
    path(
        "admin/club-rbac-advanced/<int:club_id>",
        admin.admin_club_rbac_add_advanced,
        name="admin_club_rbac_add_advanced",
    ),
    path(
        "admin/club-rbac-basic-to-advanced/<int:club_id>",
        admin.admin_club_rbac_convert_basic_to_advanced,
        name="admin_club_rbac_convert_basic_to_advanced",
    ),
    path(
        "admin/club-rbac-advanced-to-basic/<int:club_id>",
        admin.admin_club_rbac_convert_advanced_to_basic,
        name="admin_club_rbac_convert_advanced_to_basic",
    ),
    path(
        "club-menu/<int:club_id>",
        club_menu.club_menu,
        name="club_menu",
    ),
    path(
        "club-menu/<int:club_id>/<int:change_to_last_visited>",
        club_menu.club_menu,
        name="club_menu",
    ),
    path(
        "admin/access-basic/delete-user/",
        organisations.views.club_menu_tabs.access.basic_delete_user_htmx,
        name="club_admin_access_basic_delete_user_htmx",
    ),
    path(
        "admin/access-advanced/add-admin",
        organisations.views.club_menu_tabs.access.advanced_add_admin_htmx,
        name="access_advanced_add_admin_htmx",
    ),
    path(
        "admin/access-advanced/delete-user/",
        organisations.views.club_menu_tabs.access.advanced_delete_user_htmx,
        name="club_admin_access_advanced_delete_user_htmx",
    ),
    path(
        "admin/access-advanced/delete-admin/",
        organisations.views.club_menu_tabs.access.advanced_delete_admin_htmx,
        name="access_advanced_delete_admin_htmx",
    ),
    path(
        "admin/access-basic/add-user",
        organisations.views.club_menu_tabs.access.basic_add_user_htmx,
        name="club_admin_access_basic_add_user_htmx",
    ),
    path(
        "admin/access-advanced/add-user",
        organisations.views.club_menu_tabs.access.advanced_add_user_htmx,
        name="club_admin_access_advanced_add_user_htmx",
    ),
    path(
        "admin/change-rbac-to-advanced",
        organisations.views.club_menu_tabs.access.change_rbac_to_advanced_htmx,
        name="club_admin_access_change_rbac_to_advanced_htmx",
    ),
    path(
        "admin/change-rbac-to-basic",
        organisations.views.club_menu_tabs.access.change_rbac_to_basic_htmx,
        name="club_admin_access_change_rbac_to_basic_htmx",
    ),
    path(
        "club-menu/tabs/dashboard",
        club_menu.tab_dashboard_htmx,
        name="club_menu_tab_dashboard_htmx",
    ),
    path(
        "club-menu/tabs/access",
        club_menu.tab_access_htmx,
        name="club_menu_tab_access_htmx",
    ),
    path(
        "club-menu/tabs/comms/email",
        organisations.views.club_menu_tabs.comms.email_htmx,
        name="club_menu_tab_comms_email_htmx",
    ),
    path(
        "club-menu/tabs/comms/email-send",
        organisations.views.club_menu_tabs.comms.email_send_htmx,
        name="club_menu_tab_comms_email_send_htmx",
    ),
    path(
        "club-menu/tabs/comms/entrant-email-send",
        organisations.views.club_menu_tabs.comms.entrant_email_send_htmx,
        name="club_menu_tab_comms_entrant_email_send_htmx",
    ),
    path(
        "club-menu/tabs/comms/edit-inflight-batch",
        organisations.views.club_menu_tabs.comms.edit_inflight_batch_htmx,
        name="club_menu_tab_comms_edit_inflight_batch_htmx",
    ),
    path(
        "club-menu/tabs/comms/delete-inflight-batch",
        organisations.views.club_menu_tabs.comms.delete_inflight_batch_htmx,
        name="club_menu_tab_comms_delete_inflight_batch_htmx",
    ),
    path(
        "club-menu/tabs/comms/email-view",
        organisations.views.club_menu_tabs.comms.email_view_htmx,
        name="club_menu_tab_comms_email_view_htmx",
    ),
    path(
        "club-menu/tabs/settings/tags",
        organisations.views.club_menu_tabs.settings.tags_htmx,
        name="club_menu_tab_comms_tags_htmx",
    ),
    path(
        "club-menu/tabs/settings/templates",
        organisations.views.club_menu_tabs.settings.templates_htmx,
        name="club_menu_tab_comms_templates_htmx",
    ),
    path(
        "club-menu/tabs/comms/tag-delete",
        organisations.views.club_menu_tabs.comms.delete_tag_htmx,
        name="club_menu_tab_comms_tags_delete_tag_htmx",
    ),
    path(
        "club-menu/tabs/comms/tag-add-user",
        organisations.views.club_menu_tabs.comms.tags_add_user_tag,
        name="club_menu_tab_comms_tags_add_user_tag",
    ),
    path(
        "club-menu/tabs/comms/tag-remove-user",
        organisations.views.club_menu_tabs.comms.tags_remove_user_tag,
        name="club_menu_tab_comms_tags_remove_user_tag",
    ),
    path(
        "club-menu/tabs/comms/public-info",
        organisations.views.club_menu_tabs.comms.public_info_htmx,
        name="club_menu_tab_comms_public_info_htmx",
    ),
    path(
        "club-menu/tabs/congress",
        club_menu.tab_congress_htmx,
        name="club_menu_tab_congress_htmx",
    ),
    path(
        "club-menu/tabs/sessions",
        club_menu.tab_sessions_htmx,
        name="club_menu_tab_sessions_htmx",
    ),
    path(
        "club-menu/tabs/finance",
        club_menu.tab_finance_htmx,
        name="club_menu_tab_finance_htmx",
    ),
    path(
        "club-menu/tabs/finance/<int:club_id>",
        club_menu.tab_finance_statement,
        name="club_menu_tab_finance_statement",
    ),
    path(
        "club-menu/tabs/comms/edit-batch-ep/<int:club_id>/<int:batch_id_id>",
        club_menu.tab_comms_edit_batch_ep,
        name="club_menu_tab_comms_edit_batch_ep",
    ),
    path(
        "club-menu/tab-entry/<int:club_id>/<str:tab_name>",
        club_menu.tab_entry_point,
        name="club_menu_tab_entry_point",
    ),
    path(
        "club-menu/tabs/members",
        organisations.views.club_menu_tabs.members.list_htmx,
        name="club_menu_tab_members_htmx",
    ),
    path(
        "club-menu/tabs/members/add",
        organisations.views.club_menu_tabs.members.add_htmx,
        name="club_menu_tab_members_add_htmx",
    ),
    path(
        "club-menu/tabs/members/errors",
        organisations.views.club_menu_tabs.members.errors_htmx,
        name="club_menu_tab_members_errors_htmx",
    ),
    path(
        "club-menu/tabs/members/get-emails",
        organisations.views.club_menu_tabs.members.get_recent_emails_htmx,
        name="get_recent_emails_htmx",
    ),
    path(
        "club-menu/tabs/results",
        club_menu.tab_results_htmx,
        name="club_menu_tab_results_htmx",
    ),
    path(
        "club-menu/tabs/forums",
        club_menu.tab_forums_htmx,
        name="club_menu_tab_forums_htmx",
    ),
    path(
        "club-menu/tabs/settings-basic",
        organisations.views.club_menu_tabs.settings.basic_htmx,
        name="club_menu_tab_settings_basic_htmx",
    ),
    path(
        "club-menu/tabs/settings-basic-reload",
        organisations.views.club_menu_tabs.settings.basic_reload_htmx,
        name="club_menu_tab_settings_reload_basic_htmx",
    ),
    path(
        "club-menu/tabs/settings-general",
        organisations.views.club_menu_tabs.settings.general_htmx,
        name="club_menu_tab_settings_general_htmx",
    ),
    path(
        "club-menu/tabs/settings-slugs",
        organisations.views.club_menu_tabs.settings.slugs_htmx,
        name="club_menu_tab_settings_slugs_htmx",
    ),
    path(
        "club-menu/tabs/settings-results",
        organisations.views.club_menu_tabs.settings.results_htmx,
        name="club_menu_tab_settings_results_htmx",
    ),
    path(
        "club-menu/tabs/settings-slug-delete",
        organisations.views.club_menu_tabs.settings.slug_delete_htmx,
        name="club_menu_tab_settings_slug_delete_htmx",
    ),
    path(
        "club-menu/tabs/settings-slug-edit",
        organisations.views.club_menu_tabs.settings.slug_edit_htmx,
        name="club_menu_tab_settings_slug_edit_htmx",
    ),
    path(
        "club-menu/tabs/settings-slug-check-availability",
        organisations.views.club_menu_tabs.settings.slug_check_available_htmx,
        name="club_menu_tab_settings_slug_check_available_htmx",
    ),
    path(
        "club-menu/tabs/settings-slug-create-new-for-club",
        organisations.views.club_menu_tabs.settings.slug_create_new_for_club_htmx,
        name="club_menu_tab_settings_slug_create_new_for_club_htmx",
    ),
    path(
        "club-menu/tabs/settings-membership",
        organisations.views.club_menu_tabs.settings.membership_htmx,
        name="club_menu_tab_settings_membership_htmx",
    ),
    path(
        "club-menu/tabs/settings-membership-add-all",
        organisations.views.club_menu_tabs.settings.add_all_members_to_tag_htmx,
        name="club_menu_tab_settings_add_all_members_to_tag_htmx",
    ),
    path(
        "club-menu/tabs/settings-logs",
        organisations.views.club_menu_tabs.settings.logs_htmx,
        name="club_menu_tab_settings_logs_htmx",
    ),
    path(
        "club-menu/tabs/settings-edit-membership",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_membership_edit_htmx,
        name="club_menu_tab_settings_membership_edit_htmx",
    ),
    path(
        "club-menu/tabs/settings-add-membership",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_membership_add_htmx,
        name="club_menu_tab_settings_membership_add_htmx",
    ),
    path(
        "club-menu/tabs/settings-delete-membership",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_membership_delete_htmx,
        name="club_menu_tab_settings_membership_delete_htmx",
    ),
    path(
        "club-menu/tabs/members-upload-csv",
        organisations.views.club_menu_tabs.import_data.upload_csv_htmx,
        name="club_menu_tab_members_upload_csv",
    ),
    path(
        "club-menu/tabs/members-import-mpc",
        organisations.views.club_menu_tabs.import_data.import_mpc_htmx,
        name="club_menu_tab_members_import_mpc_htmx",
    ),
    path(
        "club-menu/tabs/members-edit-unreg",
        organisations.views.club_menu_tabs.members.un_reg_edit_htmx,
        name="club_menu_tab_members_un_reg_edit_htmx",
    ),
    path(
        "club-menu/tabs/members-add-member",
        organisations.views.club_menu_tabs.members.add_member_htmx,
        name="club_menu_tab_members_add_member_htmx",
    ),
    path(
        "club-menu/tabs/members-add-any-member",
        organisations.views.club_menu_tabs.members.add_any_member_htmx,
        name="club_menu_tab_members_add_any_member_htmx",
    ),
    path(
        "club-menu/tabs/members-edit-member",
        organisations.views.club_menu_tabs.members.edit_member_htmx,
        name="club_menu_tab_members_edit_member_htmx",
    ),
    path(
        "club-menu/tabs/members-search",
        organisations.views.club_menu_tabs.members.add_member_search_htmx,
        name="club_menu_tab_members_add_member_search_htmx",
    ),
    path(
        "club-menu/tabs/members-reports",
        organisations.views.club_menu_tabs.members.reports_htmx,
        name="club_menu_tab_members_reports_htmx",
    ),
    path(
        "club-menu/tabs/members-invite",
        organisations.views.club_menu_tabs.utils.invite_user_to_join_htmx,
        name="club_menu_tab_members_invite_user_to_join_htmx",
    ),
    path(
        "club-menu/tabs/members-reports-all-csv/<int:club_id>/",
        organisations.views.club_menu_tabs.members.club_admin_report_all_csv,
        name="club_menu_tab_members_report_all_csv",
    ),
    path(
        "club-menu/tabs/members-add-un-reg",
        organisations.views.club_menu_tabs.members.add_un_reg_htmx,
        name="club_menu_tab_members_add_un_reg_htmx",
    ),
    path(
        "club-menu/tabs/members-cancel-un-reg",
        organisations.views.club_menu_tabs.members.delete_un_reg_htmx,
        name="club_menu_tab_member_delete_un_reg_htmx",
    ),
    path(
        "club-menu/tabs/members-cancel-member",
        organisations.views.club_menu_tabs.members.delete_member_htmx,
        name="club_menu_tab_member_delete_member_htmx",
    ),
    path(
        "general/public-profile/<int:org_id>",
        organisations.views.general.org_profile,
        name="general_org_profile",
    ),
    path(
        "club-menu/dashboard/members-chart",
        organisations.views.club_menu_tabs.dashboard.dashboard_members_htmx,
        name="club_menu_tab_dashboard_members_htmx",
    ),
    path(
        "club-menu/dashboard/members-changes",
        organisations.views.club_menu_tabs.dashboard.dashboard_member_changes_htmx,
        name="club_menu_tab_dashboard_member_changes_htmx",
    ),
    path(
        "club-menu/dashboard/members-staff",
        organisations.views.club_menu_tabs.dashboard.dashboard_staff_htmx,
        name="club_menu_tab_dashboard_staff_htmx",
    ),
    path(
        "club-menu/settings/sessions",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_sessions_htmx,
        name="club_menu_tab_settings_sessions_htmx",
    ),
    path(
        "club-menu/settings/sessions/edit",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_session_edit_htmx,
        name="club_menu_tab_settings_session_edit_htmx",
    ),
    path(
        "club-menu/settings/payment",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_payment_htmx,
        name="club_menu_tab_settings_payment_htmx",
    ),
    path(
        "club-menu/settings/venues",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_venues_htmx,
        name="club_menu_tab_settings_venues_htmx",
    ),
    path(
        "club-menu/settings/venue-delete",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_delete_venue_htmx,
        name="club_menu_tab_settings_delete_venue_htmx",
    ),
    path(
        "club-menu/settings/payment-type-toggle",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_toggle_payment_type_htmx,
        name="club_menu_tab_settings_toggle_payment_type_htmx",
    ),
    path(
        "club-menu/settings/misc-pay-delete",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_misc_pay_delete_htmx,
        name="club_menu_tab_settings_misc_pay_delete_htmx",
    ),
    path(
        "club-menu/settings/misc-pay-add",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_misc_pay_add_htmx,
        name="club_menu_tab_settings_misc_pay_add_htmx",
    ),
    path(
        "club-menu/settings/misc-pay-amount",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_misc_pay_amount_htmx,
        name="club_menu_tab_settings_misc_pay_amount_htmx",
    ),
    path(
        "club-menu/settings/session-fee-change",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_table_fee_update_htmx,
        name="club_menu_tab_settings_table_fee_update_htmx",
    ),
    path(
        "club-menu/settings/session-delete",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_session_delete_htmx,
        name="club_menu_tab_settings_session_delete_htmx",
    ),
    path(
        "club-menu/settings/session-add",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_session_add_htmx,
        name="club_menu_tab_settings_session_add_htmx",
    ),
    path(
        "club-menu/settings/edit-template",
        organisations.views.club_menu_tabs.settings.edit_template_htmx,
        name="club_menu_tab_settings_edit_template_htmx",
    ),
    path(
        "club-menu/settings/list-template",
        organisations.views.club_menu_tabs.settings.template_list_htmx,
        name="club_menu_tab_settings_template_list_htmx",
    ),
    path(
        "club-menu/settings/template-preview",
        organisations.views.club_menu_tabs.settings.template_preview_htmx,
        name="club_menu_tab_settings_template_preview_htmx",
    ),
    path(
        "club-menu/comms/email-preview",
        organisations.views.club_menu_tabs.comms.email_preview_htmx,
        name="club_menu_tab_comms_email_preview_htmx",
    ),
    path(
        "club-menu/congress/congress-list",
        organisations.views.club_menu_tabs.congresses.congress_list_htmx,
        name="club_menu_tab_congress_list_htmx",
    ),
    path(
        "club-menu/congress/congress-list-draft",
        organisations.views.club_menu_tabs.congresses.congress_list_draft_htmx,
        name="club_menu_tab_congress_list_draft_htmx",
    ),
    path(
        "club-menu/congress/create-series-form",
        organisations.views.club_menu_tabs.congresses.create_series_htmx,
        name="club_menu_tab_congress_create_series_htmx",
    ),
    path(
        "club-menu/congress/create-series-action",
        organisations.views.club_menu_tabs.congresses.create_master_htmx,
        name="club_menu_tab_congress_create_master_htmx",
    ),
    path(
        "club-menu/congress/create-congress",
        organisations.views.club_menu_tabs.congresses.create_congress_htmx,
        name="club_menu_tab_congress_create_congress_htmx",
    ),
    path(
        "club-menu/congress/copy-congress",
        organisations.views.club_menu_tabs.congresses.copy_congress_htmx,
        name="club_menu_tab_congress_copy_congress_htmx",
    ),
    path(
        "club-menu/congress/rename-series-form",
        organisations.views.club_menu_tabs.congresses.rename_series_form_htmx,
        name="club_menu_tab_congress_rename_series_form_htmx",
    ),
    path(
        "club-menu/congress/rename-series",
        organisations.views.club_menu_tabs.congresses.rename_series_htmx,
        name="club_menu_tab_congress_rename_series_htmx",
    ),
    path(
        "club-menu/congress/delete-master",
        organisations.views.club_menu_tabs.congresses.delete_congress_master_htmx,
        name="club_menu_tab_congress_delete_congress_master_htmx",
    ),
    path(
        "club-menu/settings/templates/edit-name",
        organisations.views.club_menu_tabs.settings.edit_template_name_htmx,
        name="club_menu_tab_settings_edit_template_name_htmx",
    ),
    path(
        "club-menu/settings/welcome-pack/edit",
        organisations.views.club_menu_tabs.settings.welcome_pack_edit_htmx,
        name="club_menu_tab_settings_welcome_pack_edit_htmx",
    ),
    path(
        "club-menu/settings/welcome-pack/delete",
        organisations.views.club_menu_tabs.settings.welcome_pack_delete_htmx,
        name="club_menu_tab_settings_welcome_pack_delete_htmx",
    ),
    path(
        "club-menu/settings/welcome-pack/view",
        organisations.views.club_menu_tabs.settings.welcome_pack_htmx,
        name="club_menu_tab_settings_welcome_pack_htmx",
    ),
    path(
        "club-menu/settings/templates/edit-from-name",
        organisations.views.club_menu_tabs.settings.edit_from_name_htmx,
        name="club_menu_tab_settings_edit_from_name_htmx",
    ),
    path(
        "club-menu/settings/templates/edit-reply-to",
        organisations.views.club_menu_tabs.settings.edit_reply_to_htmx,
        name="club_menu_tab_settings_edit_reply_to_htmx",
    ),
    path(
        "club-menu/settings/templates/from-and-reply-to",
        organisations.views.club_menu_tabs.comms.from_and_reply_to_htmx,
        name="club_menu_tab_comms_from_and_reply_to_htmx",
    ),
    path(
        "club-menu/settings/templates/edit-banner",
        organisations.views.club_menu_tabs.settings.edit_template_banner_htmx,
        name="club_menu_tab_settings_edit_template_banner_htmx",
    ),
    path(
        "club-menu/settings/templates/delete",
        organisations.views.club_menu_tabs.settings.delete_template_htmx,
        name="club_menu_tab_settings_delete_template_htmx",
    ),
    path(
        "club-menu/comms/email-attachments/view",
        organisations.views.club_menu_tabs.comms.email_attachment_htmx,
        name="club_menu_tab_comms_email_attachment_htmx",
    ),
    path(
        "club-menu/comms/email-attachments/upload",
        organisations.views.club_menu_tabs.comms.upload_new_email_attachment_htmx,
        name="club_menu_tab_comms_upload_new_email_attachment_htmx",
    ),
    path(
        "club-menu/comms/email-attachments/delete",
        organisations.views.club_menu_tabs.comms.delete_email_attachment_htmx,
        name="club_menu_tab_comms_delete_email_attachment_htmx",
    ),
    path(
        "club-menu/settings/users-with-tag",
        organisations.views.club_menu_tabs.settings.users_with_tag_htmx,
        name="club_menu_tab_settings_users_with_tag_htmx",
    ),
    path(
        "club-menu/settings/delete-user-from-tag",
        organisations.views.club_menu_tabs.settings.delete_user_from_tag_htmx,
        name="club_menu_tab_settings_delete_user_from_tag_htmx",
    ),
    path(
        "club-menu/settings/add-user-to-tag",
        organisations.views.club_menu_tabs.settings.add_user_to_tag_htmx,
        name="club_menu_tab_settings_add_user_to_tag_htmx",
    ),
    path(
        "club-menu/results/upload-results-file",
        organisations.views.club_menu_tabs.results.upload_results_file_htmx,
        name="club_menu_tab_results_upload_results_file",
    ),
    path(
        "club-menu/results/update-results-email-message",
        organisations.views.club_menu_tabs.results.update_results_email_message_htmx,
        name="club_menu_tab_results_update_results_email_message_htmx",
    ),
    path(
        "club-menu/results/toggle-result-publish-state",
        organisations.views.club_menu_tabs.results.toggle_result_publish_state_htmx,
        name="club_menu_tab_results_toggle_result_publish_state_htmx",
    ),
    path(
        "club-menu/results/delete-results-file",
        organisations.views.club_menu_tabs.results.delete_results_file_htmx,
        name="club_menu_tab_results_delete_results_file_htmx",
    ),
    path(
        "club-menu/settings/payment-edit-name",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_payment_edit_name_htmx,
        name="club_menu_tab_settings_payment_edit_name_htmx",
    ),
    path(
        "club-menu/settings/tag-edit-name",
        organisations.views.club_menu_tabs.settings.club_menu_tab_settings_tag_edit_name_htmx,
        name="club_menu_tab_settings_tag_edit_name_htmx",
    ),
    path(
        "club-menu/settings/emails_from_tags",
        organisations.views.club_menu_tabs.comms.club_menu_tab_comms_emails_from_tags_htmx,
        name="club_menu_tab_comms_emails_from_tags_htmx",
    ),
    path(
        "club-menu/comms/email-recipients-list",
        organisations.views.club_menu_tabs.comms.email_recipients_list_htmx,
        name="club_menu_tab_comms_email_recipients_list_htmx",
    ),
    # JPG deprecate - replaced
    path(
        "club-menu/member/add-misc-payment",
        organisations.views.club_menu_tabs.members.add_misc_payment_htmx,
        name="club_menu_tab_members_add_misc_payment_htmx",
    ),
    path(
        "club-menu/finance/cancel-user-pending-debt",
        organisations.views.club_menu_tabs.finance.cancel_user_pending_debt_htmx,
        name="club_menu_tab_finance_cancel_user_pending_debt_htmx",
    ),
    # path(
    #     "club-menu/member/recent-payments-for-user",
    #     organisations.views.club_menu_tabs.members.recent_payments_for_user_htmx,
    #     name="club_menu_tab_members_recent_payments_for_user_htmx",
    # ),
    path(
        "member/get-member-balance",
        organisations.views.club_menu_tabs.members.get_member_balance_htmx,
        name="get_member_balance_htmx",
    ),
    path(
        "finance/transactions",
        organisations.views.club_menu_tabs.finance.transactions_htmx,
        name="transactions_htmx",
    ),
    path(
        "finance/transaction-filter",
        organisations.views.club_menu_tabs.finance.transaction_filter_htmx,
        name="transaction_filter_htmx",
    ),
    path(
        "finance/pay-member",
        organisations.views.club_menu_tabs.finance.pay_member_htmx,
        name="pay_member_htmx",
    ),
    path(
        "finance/charge-member",
        organisations.views.club_menu_tabs.finance.charge_member_htmx,
        name="charge_member_htmx",
    ),
    path(
        "finance/pay-org",
        organisations.views.club_menu_tabs.finance.pay_org_htmx,
        name="pay_org_htmx",
    ),
    path(
        "org-search-generic",
        organisations.views.general.generic_org_search_htmx,
        name="generic_org_search_htmx",
    ),
    path(
        "finance/transaction-details",
        organisations.views.club_menu_tabs.finance.transaction_details_htmx,
        name="transaction_details_htmx",
    ),
    path(
        "finance/transaction-session-details",
        organisations.views.club_menu_tabs.finance.transaction_session_details_htmx,
        name="transaction_session_details_htmx",
    ),
    path(
        "finance/transaction-event-details",
        organisations.views.club_menu_tabs.finance.transaction_event_details_htmx,
        name="transaction_event_details_htmx",
    ),
    path(
        "finance/transaction-congress-details",
        organisations.views.club_menu_tabs.finance.transaction_congress_details_htmx,
        name="transaction_congress_details_htmx",
    ),
    # JPG clean up
    # path(
    #     "member/search-tab",
    #     organisations.views.club_menu_tabs.members.member_search_tab_htmx,
    #     name="member_search_tab_htmx",
    # ),
    # path(
    #     "member/search-tab-name",
    #     organisations.views.club_menu_tabs.members.member_search_tab_name_htmx,
    #     name="member_search_tab_name_htmx",
    # ),
    # path(
    #     "member/search-tab-email",
    #     organisations.views.club_menu_tabs.members.member_search_tab_email_htmx,
    #     name="member_search_tab_email_htmx",
    # ),
    path(
        "sessions/refresh-sessions-tab",
        organisations.views.club_menu_tabs.sessions.refresh_sessions_tab,
        name="refresh_sessions_tab",
    ),
    path(
        "sessions/delete-session",
        organisations.views.club_menu_tabs.sessions.delete_session_htmx,
        name="delete_session_htmx",
    ),
    path(
        "sessions/club-menu-tab-sessions-sub",
        organisations.views.club_menu_tabs.sessions.club_menu_tab_sessions_sub_htmx,
        name="club_menu_tab_sessions_sub_htmx",
    ),
    path(
        "general/default_secondary_payment_method",
        organisations.views.club_menu_tabs.settings.default_secondary_payment_method_htmx,
        name="club_menu_tab_settings_default_secondary_payment_method_htmx",
    ),
    path(
        "settings/edit_minimum_balance_after_settlement_htmx",
        organisations.views.club_menu_tabs.settings.edit_minimum_balance_after_settlement_htmx,
        name="club_menu_tab_settings_edit_minimum_balance_after_settlement_htmx",
    ),
    path(
        "admin/convert_manual_club_to_automatic/<int:club_id>",
        organisations.views.admin.convert_manual_club_to_automatic,
        name="admin_convert_manual_club_to_automatic",
    ),
    path(
        "member/bulk-invite-to-join",
        organisations.views.club_menu_tabs.members.bulk_invite_to_join_htmx,
        name="club_menu_tab_members_bulk_invite_to_join_htmx",
    ),
    path(
        "member/unblock-unreg-email-address",
        organisations.views.club_menu_tabs.members.unblock_unreg_email_address_htmx,
        name="club_menu_tab_members_unblock_unreg_email_address_htmx",
    ),
    path(
        "member/recent-sessions-for-member",
        organisations.views.club_menu_tabs.members.recent_sessions_for_member_htmx,
        name="club_menu_tab_members_recent_sessions_for_member_htmx",
    ),
    path(
        "settings/toggle-use-last-payment-method-for-player-sessions",
        organisations.views.club_menu_tabs.settings.toggle_use_last_payment_method_for_player_sessions_htmx,
        name="club_menu_tab_settings_use_last_payment_method_for_player_sessions_htmx",
    ),
    # -----------------------------------------------------------------------------------
    #   Club admin
    # -----------------------------------------------------------------------------------
    path(
        "club-admin/search-tab",
        organisations.views.club_admin.search_tab_htmx,
        name="search_tab_htmx",
    ),
    path(
        "club-admin/search-tab-name",
        organisations.views.club_admin.search_tab_name_htmx,
        name="search_tab_name_htmx",
    ),
    path(
        "club-admin/search-tab-email",
        organisations.views.club_admin.search_tab_email_htmx,
        name="search_tab_email_htmx",
    ),
    path(
        "club-menu/tabs/members-reports-active-csv/<int:club_id>/",
        organisations.views.club_menu_tabs.members.club_admin_report_active_csv,
        name="club_menu_tab_members_report_active_csv",
    ),
    # -----------------------------------------------------------------------------------
    #   Club admin - Edit member
    # -----------------------------------------------------------------------------------
    path(
        "club-admin/add-member",
        organisations.views.club_menu_tabs.members.club_admin_add_member_htmx,
        name="club_admin_add_member_htmx",
    ),
    path(
        "club-admin/add-member/detail",
        organisations.views.club_menu_tabs.members.club_admin_add_member_detail_htmx,
        name="club_admin_add_member_detail_htmx",
    ),
    # -----------------------------------------------------------------------------------
    #   Club admin - Edit member
    # -----------------------------------------------------------------------------------
    path(
        "club-admin/edit-member-htmx",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_htmx,
        name="club_admin_edit_member_htmx",
    ),
    #
    #   Club admin - Edit member - Action button end points
    #
    path(
        "club-admin/edit-member/action/",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_membership_action_htmx,
        name="club_admin_edit_member_membership_action_htmx",
    ),
    path(
        "club-admin/edit-member/change/",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_change_htmx,
        name="club_admin_edit_member_change_htmx",
    ),
    path(
        "club-admin/edit-member/extend/",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_extend_htmx,
        name="club_admin_edit_member_extend_htmx",
    ),
    path(
        "club-admin/edit-member/payment/",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_payment_htmx,
        name="club_admin_edit_member_payment_htmx",
    ),
    path(
        "club-admin/edit-member/membership/edit",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_edit_mmt_htmx,
        name="club_admin_edit_member_edit_mmt_htmx",
    ),
    path(
        "club-admin/edit-member/membership/delete",
        organisations.views.club_menu_tabs.members.club_admin_edit_member_delete_mmt_htmx,
        name="club_admin_edit_member_delete_mmt_htmx",
    ),
    # -----------------------------------------------------------------------------------
    #   Club admin - Recent activity views - common to members and contacts
    # -----------------------------------------------------------------------------------
    path(
        "club-admin/activity/tags",
        organisations.views.club_admin.activity_tags_htmx,
        name="club_admin_activity_tags_htmx",
    ),
    path(
        "club-admin/activity/emails",
        organisations.views.club_admin.activity_emails_htmx,
        name="club_admin_activity_emails_htmx",
    ),
    path(
        "club-admin/activity/entries",
        organisations.views.club_admin.activity_entries_htmx,
        name="club_admin_activity_entries_htmx",
    ),
    path(
        "club-admin/activity/sessions",
        organisations.views.club_admin.activity_sessions_htmx,
        name="club_admin_activity_sessions_htmx",
    ),
    path(
        "club-admin/activity/transactions",
        organisations.views.club_admin.activity_transactions_htmx,
        name="club_admin_activity_transactions_htmx",
    ),
    path(
        "club-admin/activity/transactions/transact",
        organisations.views.club_admin.add_misc_payment_htmx,
        name="club_admin_add_misc_payment_htmx",
    ),
    path(
        "club-admin/activity/invitations",
        organisations.views.club_admin.activity_invitations_htmx,
        name="club_admin_activity_invitations_htmx",
    ),
    path(
        "club-admin/activity/none",
        organisations.views.club_admin.activity_none_htmx,
        name="club_admin_activity_none_htmx",
    ),
    # -----------------------------------------------------------------------------------
    #   Club admin - Contacts
    # -----------------------------------------------------------------------------------
    path(
        "club-menu/tabs/contacts",
        organisations.views.club_menu_tabs.contacts.list_htmx,
        name="club_menu_tab_contacts_htmx",
    ),
    path(
        "club-menu/tabs/contacts/add",
        organisations.views.club_menu_tabs.contacts.add_htmx,
        name="club_menu_tab_contacts_add_htmx",
    ),
    path(
        "club-menu/tabs/contacts/edit",
        organisations.views.club_menu_tabs.contacts.edit_htmx,
        name="club_admin_tab_edit_contact_htmx",
    ),
    path(
        "club-menu/tabs/contacts/delete",
        organisations.views.club_menu_tabs.contacts.delete_htmx,
        name="club_admin_delete_contact_htmx",
    ),
    path(
        "club-menu/tabs/contacts/convert-select",
        organisations.views.club_menu_tabs.contacts.convert_select_system_number_htmx,
        name="club_admin_edit_covert_contact_select_htmx",
    ),
    path(
        "club-menu/tabs/contacts/convert",
        organisations.views.club_menu_tabs.contacts.convert_htmx,
        name="club_admin_edit_covert_contact_htmx",
    ),
    path(
        "club-menu/tabs/contacts/convert-wrapper",
        organisations.views.club_menu_tabs.members.club_admin_convert_add_contact_wrapper_htmx,
        name="club_admin_add_covert_contact_wrapper_htmx",
    ),
    path(
        "club-menu/tabs/contacts/add/individual-system",
        organisations.views.club_menu_tabs.contacts.add_contact_manual_htmx,
        name="club_admin_add_contact_manual_htmx",
    ),
    path(
        "club-menu/tabs/contacts/add/individual-internal",
        organisations.views.club_menu_tabs.contacts.add_individual_internal_htmx,
        name="club_admin_add_contact_individual_internal_htmx",
    ),
    # path(
    #     "club-menu/tabs/contacts/add/upload",
    #     organisations.views.club_menu_tabs.contacts.upload_csv_htmx,
    #     name="club_admin_add_contact_upload_csv_htmx",
    # ),
    path(
        "club-menu/tabs/contacts/add/search",
        organisations.views.club_menu_tabs.contacts.add_search_htmx,
        name="club_menu_tab_members_add_contact_search_htmx",
    ),
    path(
        "club-menu/tabs/contacts-upload-csv",
        organisations.views.club_menu_tabs.import_data.contact_upload_csv_htmx,
        name="club_menu_tab_contacts_upload_csv",
    ),
    path(
        "club-menu/tabs/contacts-reports",
        organisations.views.club_menu_tabs.contacts.reports_htmx,
        name="club_menu_tab_contacts_reports_htmx",
    ),
    path(
        "club-menu/tabs/contacts-reports-all-csv/<int:club_id>/",
        organisations.views.club_menu_tabs.contacts.club_admin_report_all_csv,
        name="club_menu_tab_contacts_report_all_csv",
    ),
    # -----------------------------------------------------------------------------------
    #   Club admin - Renewals
    # -----------------------------------------------------------------------------------
    path(
        "club-admin/user-initiated-payment/<int:mmt_id>/",
        organisations.views.club_admin.user_initiated_payment,
        name="club_admin_user_initiated_payment",
    ),
    path(
        "club-admin/user-initiated-payment-success/<int:mmt_id>/",
        organisations.views.club_admin.user_initiated_payment_success_htmx,
        name="club_admin_user_initiated_payment_success_htmx",
    ),
    path(
        "club-admin/renewals/menu",
        organisations.views.club_menu_tabs.members.renewals_menu_htmx,
        name="club_menu_tab_members_renewals_menu_htmx",
    ),
    path(
        "club-admin/renewals/bulk",
        organisations.views.club_menu_tabs.members.bulk_renewals_htmx,
        name="club_menu_tab_members_bulk_renewal_htmx",
    ),
    path(
        "club-admin/renewals/bulk/test",
        organisations.views.club_menu_tabs.members.bulk_renewals_test_htmx,
        name="club_menu_tab_members_bulk_renewal_test_htmx",
    ),
    path(
        "club-admin/renewals/unpaid",
        organisations.views.club_menu_tabs.members.view_unpaid_htmx,
        name="club_menu_tab_members_view_unpaid_htmx",
    ),
    path(
        "club-admin/renewals/email-unpaid/<int:club_id>/",
        organisations.views.club_menu_tabs.members.email_unpaid,
        name="club_menu_tab_members_email_unpaid",
    ),
]
