# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import path

import organisations.views.club_menu
import organisations.views.club_menu_tabs.access
import organisations.views.club_menu_tabs.comms
import organisations.views.club_menu_tabs.dashboard
import organisations.views.club_menu_tabs.import_data
import organisations.views.club_menu_tabs.members
import organisations.views.club_menu_tabs.settings
import organisations.views.club_menu_tabs.utils
from .views import club_menu, ajax

from .views import admin
from .views import general

app_name = "organisations"  # pylint: disable=invalid-name

urlpatterns = [
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
        "admin/access-basic/delete-user/",
        organisations.views.club_menu_tabs.access.basic_delete_user_htmx,
        name="club_admin_access_basic_delete_user_htmx",
    ),
    path(
        "admin/access-advanced/delete-admin",
        organisations.views.club_menu_tabs.access.advanced_add_admin_htmx,
        name="access_advanced_add_admin_htmx",
    ),
    path(
        "admin/access-advanced/delete-user/",
        organisations.views.club_menu_tabs.access.advanced_delete_user_htmx,
        name="club_admin_access_advanced_delete_user_htmx",
    ),
    path(
        "admin/access-advanced/delete-admin/<int:club_id>/<int:user_id>",
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
        "club-menu/tabs/comms/email-view",
        organisations.views.club_menu_tabs.comms.email_view_htmx,
        name="club_menu_tab_comms_email_view_htmx",
    ),
    path(
        "club-menu/tabs/comms/tags",
        organisations.views.club_menu_tabs.comms.tags_htmx,
        name="club_menu_tab_comms_tags_htmx",
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
        "club-menu/tabs/finance",
        club_menu.tab_finance_htmx,
        name="club_menu_tab_finance_htmx",
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
        "club-menu/tabs/settings-membership",
        organisations.views.club_menu_tabs.settings.membership_htmx,
        name="club_menu_tab_settings_membership_htmx",
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
        "club-menu/tabs/members-edit-member",
        organisations.views.club_menu_tabs.members.edit_member_htmx,
        name="club_menu_tab_members_edit_member_htmx",
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
        organisations.views.club_menu_tabs.members.report_all_csv,
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
        "public-profile/<int:org_id>",
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
]
