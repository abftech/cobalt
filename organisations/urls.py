# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import path

import organisations.views.club_menu
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
        "admin/access-basic/delete-user/<int:club_id>/<int:user_id>",
        organisations.views.club_menu.access_basic_delete_user_htmx,
        name="club_admin_access_basic_delete_user_htmx",
    ),
    path(
        "admin/access-advanced/delete-admin",
        organisations.views.club_menu.access_advanced_add_admin_htmx,
        name="access_advanced_add_admin_htmx",
    ),
    path(
        "admin/access-advanced/delete-user/<int:club_id>/<int:user_id>/<str:group_name_item>",
        organisations.views.club_menu.access_advanced_delete_user_htmx,
        name="club_admin_access_advanced_delete_user_htmx",
    ),
    path(
        "admin/access-advanced/delete-admin/<int:club_id>/<int:user_id>",
        organisations.views.club_menu.access_advanced_delete_admin_htmx,
        name="access_advanced_delete_admin_htmx",
    ),
    path(
        "admin/access-basic/add-user",
        organisations.views.club_menu.access_basic_add_user_htmx,
        name="club_admin_access_basic_add_user_htmx",
    ),
    path(
        "admin/access-advanced/add-user",
        organisations.views.club_menu.access_advanced_add_user_htmx,
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
        "club-menu/tabs/comms",
        club_menu.tab_comms_htmx,
        name="club_menu_tab_comms_htmx",
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
        club_menu.tab_members_htmx,
        name="club_menu_tab_members_htmx",
    ),
    path(
        "club-menu/tabs/results",
        club_menu.tab_results_htmx,
        name="club_menu_tab_results_htmx",
    ),
    path(
        "club-menu/tabs/settings-basic",
        club_menu.tab_settings_basic_htmx,
        name="club_menu_tab_settings_basic_htmx",
    ),
    path(
        "club-menu/tabs/settings-basic-reload",
        club_menu.tab_settings_basic_reload_htmx,
        name="club_menu_tab_settings_reload_basic_htmx",
    ),
    path(
        "club-menu/tabs/settings-membership",
        club_menu.tab_settings_membership_htmx,
        name="club_menu_tab_settings_membership_htmx",
    ),
    path(
        "club-menu/tabs/settings-edit-membership",
        club_menu.club_menu_tab_settings_membership_edit_htmx,
        name="club_menu_tab_settings_membership_edit_htmx",
    ),
]
