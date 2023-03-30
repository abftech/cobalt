from django.urls import path

import events.views.global_admin
from .views import congress_admin, ajax, congress_builder, views

app_name = "events"  # pylint: disable=invalid-name

urlpatterns = [
    #################################
    # Screens for normal players    #
    #################################
    path("", views.congress_listing, name="congress_listing"),
    path(
        "congress-listing/<str:reverse_list>",
        views.congress_listing,
        name="congress_listing",
    ),
    path(
        "congress-listing-data",
        views.congress_listing_data_htmx,
        name="congress_listing_data_htmx",
    ),
    path("congress/view/<int:congress_id>", views.view_congress, name="view_congress"),
    path(
        "congress/view/<int:congress_id>/<int:fullscreen>",
        views.view_congress,
        name="view_congress",
    ),
    path(
        "congress/event/enter/<int:congress_id>/<int:event_id>",
        views.enter_event,
        name="enter_event",
    ),
    path(
        "congress/event/enter/<int:congress_id>/<int:event_id>/<int:enter_for_another>",
        views.enter_event,
        name="enter_event_for_another",
    ),
    path(
        "congress/event/enter/success",
        views.enter_event_success,
        name="enter_event_success",
    ),
    path(
        "congress/event/enter/payment-fail",
        views.enter_event_payment_fail,
        name="enter_event_payment_fail",
    ),
    path(
        "congress/event/view-event-entries/<int:congress_id>/<int:event_id>",
        views.view_event_entries,
        name="view_event_entries",
    ),
    path(
        "congress/event/view-event-partnership-desk/<int:congress_id>/<int:event_id>",
        views.view_event_partnership_desk,
        name="view_event_partnership_desk",
    ),
    path(
        "congress/event/change-entry/<int:congress_id>/<int:event_id>",
        views.edit_event_entry,
        name="edit_event_entry",
    ),
    # as above but includes event_entry_id so primary_entrant can edit other entries they have made
    path(
        "congress/event/change-entry/<int:event_entry_id>",
        views.edit_event_entry,
        name="edit_event_entry",
    ),
    # as above with status message
    path(
        "congress/event/change-entry/<int:event_entry_id>/<str:pay_status>",
        views.edit_event_entry,
        name="edit_event_entry",
    ),
    # as above but accepts edit=1 to open window with edit enabled
    # path(
    #     "congress/event/change-entry/<int:congress_id>/<int:event_id>/edit=<int:edit_flag>",
    #     views.edit_event_entry,
    #     name="edit_event_entry",
    # ),
    # # as above with extra parameter for messages after pay now pressed
    path(
        "congress/event/change-entry/<int:congress_id>/<int:event_id>/<str:pay_status>",
        views.edit_event_entry,
        name="edit_event_entry",
    ),
    path(
        "congress/event/change-answer/<int:event_entry_id>/<str:answer>",
        ajax.change_answer_on_existing_entry_ajax,
        name="change_answer_on_existing_entry_ajax",
    ),
    path(  # dummy entry for no parameters
        "congress/event/change-answer",
        ajax.change_answer_on_existing_entry_ajax,
        name="change_answer_on_existing_entry_ajax",
    ),
    path(
        "congress/event/change-category/<int:event_entry_id>/<int:category_id>",
        ajax.change_category_on_existing_entry_ajax,
        name="change_category_on_existing_entry_ajax",
    ),
    path(  # dummy entry for no parameters
        "congress/event/change-category",
        ajax.change_category_on_existing_entry_ajax,
        name="change_category_on_existing_entry_ajax",
    ),
    path(
        "congress/get_all_congresses",
        ajax.get_all_congress_ajax,
        name="test_tanmay_ajax",
    ),
    path(
        "congress/event/delete-entry/<int:event_entry_id>",
        views.delete_event_entry,
        name="delete_event_entry",
    ),
    path(
        "congress/event/third-party-checkout-player/<int:event_entry_player_id>",
        views.third_party_checkout_player,
        name="third_party_checkout_player",
    ),
    path(  # dummy for entry above
        "congress/event/third-party-checkout-player",
        views.third_party_checkout_player,
        name="third_party_checkout_player",
    ),
    path(
        "congress/event/third-party-checkout-entry/<int:event_entry_id>",
        views.third_party_checkout_entry,
        name="third_party_checkout_entry",
    ),
    path(
        "congress/checkout",
        views.checkout,
        name="checkout",
    ),
    path(
        "congress/create/edit-session/<int:event_id>/<int:session_id>",
        congress_builder.edit_session,
        name="edit_session",
    ),
    path("congress/teammate/checkout", views.pay_outstanding, name="pay_outstanding"),
    path(
        "congress/create/delete-event",
        ajax.delete_event_ajax,
        name="delete_event_ajax",
    ),
    path(
        "congress/event/enter/fee-for-user",
        ajax.fee_for_user_ajax,
        name="fee_for_user_ajax",
    ),
    path(
        "congress/event/enter/payment-options-for-user",
        ajax.payment_options_for_user_ajax,
        name="payment_options_for_user_ajax",
    ),
    path(
        "congress/event/delete-basket-item",
        ajax.delete_basket_item_ajax,
        name="delete_basket_item_ajax",
    ),
    path(
        "congress/event/check-player-entry",
        ajax.check_player_entry_ajax,
        name="check_player_entry_ajax",
    ),
    path(
        "congress/event/change-player-entry",
        ajax.change_player_entry_ajax,
        name="change_player_entry_ajax",
    ),
    path(
        "congress/event/add-player-to-entry",
        ajax.add_player_to_existing_entry_ajax,
        name="add_player_to_existing_entry_ajax",
    ),
    path(
        "congress/event/delete-player-from-entry",
        ajax.delete_player_from_entry_ajax,
        name="delete_player_from_entry_ajax",
    ),
    path(
        "congress/event/contact_partnership_desk_person",
        ajax.contact_partnership_desk_person_ajax,
        name="contact_partnership_desk_person_ajax",
    ),
    path(
        "congress/event/delete-me-from-partnership-desk/<int:event_id>",
        ajax.delete_me_from_partnership_desk,
        name="delete_me_from_partnership_desk",
    ),
    path(  # dummy for entry above
        "congress/event/delete-me-from-partnership-desk",
        ajax.delete_me_from_partnership_desk,
        name="delete_me_from_partnership_desk",
    ),
    path(
        "view",
        views.view_events,
        name="view_events",
    ),
    path(
        "congress/event/partnership-desk-signup/<int:congress_id>/<int:event_id>",
        views.partnership_desk_signup,
        name="partnership_desk_signup",
    ),
    path(
        "congress/event/change-payment-method-on-existing-entry-ajax",
        ajax.change_payment_method_on_existing_entry_ajax,
        name="change_payment_method_on_existing_entry_ajax",
    ),
    path(
        "congress/event/edit-comment-for-entry",
        ajax.edit_comment_event_entry_ajax,
        name="save_comment_for_event_entry_ajax",
    ),
    path(
        "congress/event/edit-team_name-for-entry",
        ajax.edit_team_name_event_entry_ajax,
        name="edit_team_name_event_entry_ajax",
    ),
    path(
        "congress/event/edit-player_name-for-entry",
        congress_admin.edit_player_name_htmx,
        name="admin_edit_player_name_htmx",
    ),
    path(
        "congress/event/edit-tba-player-for-entry",
        congress_admin.edit_tba_player_details_htmx,
        name="admin_edit_tba_player_details_htmx",
    ),
    path(
        "show-congresses-for-club",
        views.show_congresses_for_club_htmx,
        name="show_congresses_for_club_htmx",
    ),
    path(
        "get-other-entries-to-event-for-user/<int:event_id>/<int:this_event_entry_id>",
        views.get_other_entries_to_event_for_user_htmx,
        name="get_other_entries_to_event_for_user_htmx",
    ),
    path(
        "get-player-payment-amount-ajax",
        ajax.get_player_payment_amount_ajax,
        name="get_player_payment_amount_ajax",
    ),
    path(
        "give-player-refund-ajax",
        ajax.give_player_refund_ajax,
        name="give_player_refund_ajax",
    ),
    path(
        "save-congress-view-filters-ajax",
        ajax.save_congress_view_filters_ajax,
        name="save_congress_view_filters_ajax",
    ),
    path(
        "clear-congress-view-filters-ajax",
        ajax.clear_congress_view_filters_ajax,
        name="clear_congress_view_filters_ajax",
    ),
    path(
        "load-congress-view-filters-ajax",
        ajax.load_congress_view_filters_ajax,
        name="load_congress_view_filters_ajax",
    ),
    ########################################################################
    # Congress Builder screens for conveners to create and edit congresses #
    ########################################################################
    path(
        "congress-builder/delete/<int:congress_id>",
        congress_builder.delete_congress,
        name="delete_congress",
    ),
    path(
        "congress-builder/create/wizard",
        congress_builder.create_congress_wizard,
        name="create_congress_wizard",
    ),
    path(
        "congress-builder/create/wizard/<int:step>",
        congress_builder.create_congress_wizard,
        name="create_congress_wizard",
    ),
    path(
        "congress-builder/create/wizard/<int:congress_id>/<int:step>",
        congress_builder.create_congress_wizard,
        name="create_congress_wizard",
    ),
    path(
        "congress-builder/create/wizard/downloads/<int:congress_id>",
        congress_builder.manage_congress_download,
        name="manage_congress_download",
    ),
    path(
        "congress-builder/get-conveners/<int:org_id>",
        ajax.get_conveners_ajax,
        name="get_conveners_ajax",
    ),
    path(
        "congress-builder/create/get-congress-master/<int:org_id>",
        ajax.get_congress_master_ajax,
        name="get_congress_master_ajax",
    ),
    path(
        "congress-builder/create/get-congress/<int:congress_id>",
        ajax.get_congress_ajax,
        name="get_congress_ajax",
    ),
    path(
        "congress-builder/create/add-event/<int:congress_id>",
        congress_builder.create_event,
        name="create_event",
    ),
    path(
        "congress-builder/create/edit-event/<int:congress_id>/<int:event_id>",
        congress_builder.edit_event,
        name="edit_event",
    ),
    # javascript parameter missing call for function above
    path(
        "congress-builder/create/edit-event/<int:congress_id>",
        congress_builder.edit_event,
        name="edit_event",
    ),
    path(
        "congress-builder/create/add-session/<int:event_id>",
        congress_builder.create_session,
        name="create_session",
    ),
    path(
        "congress-builder/create/delete-category",
        ajax.delete_category_ajax,
        name="delete_category_ajax",
    ),
    path(
        "congress-builder/create/edit-category",
        ajax.edit_category_ajax,
        name="edit_category_ajax",
    ),
    path(
        "congress-builder/create/delete-session",
        ajax.delete_session_ajax,
        name="delete_session_ajax",
    ),
    path(
        "congress-builder/create/add-category",
        ajax.add_category_ajax,
        name="add_category_ajax",
    ),
    path(
        "congress-builder/view-draft",
        congress_builder.view_draft_congresses,
        name="view_draft_congresses",
    ),
    path(
        "congress-builder/slug-handler",
        congress_builder.slug_handler_htmx,
        name="slug_handler_htmx",
    ),
    ########################################################################
    # Congress Admin screens for conveners to manage an existing congress  #
    ########################################################################
    path(
        "congress-admin/summary/<int:congress_id>",
        congress_admin.admin_summary,
        name="admin_summary",
    ),
    path(
        "congress-admin/summary/event/<int:event_id>",
        congress_admin.admin_event_summary,
        name="admin_event_summary",
    ),
    path(
        "congress-admin/email/event/<int:event_id>",
        congress_admin.admin_event_email,
        name="admin_event_email",
    ),
    path(
        "congress-admin/email/congress/<int:congress_id>",
        congress_admin.admin_congress_email,
        name="admin_congress_email",
    ),
    path(
        "congress-admin/email/event-unpaid/<int:event_id>",
        congress_admin.admin_unpaid_email,
        name="admin_unpaid_email",
    ),
    path(
        "congress-admin/summary/event-player-discount/<int:event_id>",
        congress_admin.admin_event_player_discount,
        name="admin_event_player_discount",
    ),
    path(
        "congress-admin/detail/event-entry/<int:evententry_id>",
        congress_admin.admin_evententry,
        name="admin_evententry",
    ),
    path(
        "congress-admin/player_events_list/<int:member_id>/<int:congress_id>",
        congress_admin.player_events_list,
        name="admin_player_events_list",
    ),
    path(
        "congress-admin/detail/event-entry-delete/<int:evententry_id>",
        congress_admin.admin_evententry_delete,
        name="admin_evententry_delete",
    ),
    path(
        "congress-admin/detail/event-entry-player/<int:evententryplayer_id>",
        congress_admin.admin_evententryplayer,
        name="admin_evententryplayer",
    ),
    path(
        "congress-admin/event-csv/<int:event_id>",
        congress_admin.admin_event_csv,
        name="admin_event_csv",
    ),
    path(
        "congress-admin/event-csv-scoring/<int:event_id>",
        congress_admin.admin_event_csv_scoring,
        name="admin_event_csv_scoring",
    ),
    path(
        "congress-admin/congress-csv-scoring/<int:congress_id>",
        congress_admin.admin_congress_csv_scoring,
        name="admin_congress_csv_scoring",
    ),
    path(
        "congress-admin/event-log/<int:event_id>",
        congress_admin.admin_event_log,
        name="admin_event_log",
    ),
    path(
        "congress-admin/event-unpaid/<int:event_id>",
        congress_admin.admin_event_unpaid,
        name="admin_event_unpaid",
    ),
    path(
        "congress-admin/event-players_report/<int:event_id>",
        congress_admin.admin_players_report,
        name="admin_players_report",
    ),
    path(
        "congress-admin/event-offsystem/<int:event_id>",
        congress_admin.admin_event_offsystem,
        name="admin_event_offsystem",
    ),
    path(
        "congress-admin/event-offsystem-pp/<int:event_id>",
        congress_admin.admin_event_offsystem_pp,
        name="admin_event_offsystem_pp",
    ),
    path(
        "congress-admin/event-offsystem-pp-batch/<int:event_id>",
        congress_admin.admin_event_offsystem_pp_batch,
        name="admin_event_offsystem_pp_batch",
    ),
    path(
        "congress-admin/off-system/pay",
        ajax.admin_offsystem_pay_ajax,
        name="admin_offsystem_pay_ajax",
    ),
    path(
        "congress-admin/off-system-pp/unpay",
        ajax.admin_offsystem_unpay_pp_ajax,
        name="admin_offsystem_unpay_pp_ajax",
    ),
    path(
        "congress-admin/off-system-pp/pay",
        ajax.admin_offsystem_pay_pp_ajax,
        name="admin_offsystem_pay_pp_ajax",
    ),
    path(
        "congress-admin/off-system/unpay",
        ajax.admin_offsystem_unpay_ajax,
        name="admin_offsystem_unpay_ajax",
    ),
    path(
        "congress-admin/player-discount/delete",
        ajax.admin_player_discount_delete_ajax,
        name="admin_player_discount_delete_ajax",
    ),
    path(
        "congress-admin/bulletins/<int:congress_id>",
        congress_admin.admin_bulletins,
        name="admin_bulletins",
    ),
    path(
        "congress-admin/latest-news/<int:congress_id>",
        congress_admin.admin_latest_news,
        name="admin_latest_news",
    ),
    path(
        "congress-admin/bulletin/delete",
        ajax.admin_delete_bulletin_ajax,
        name="admin_delete_bulletin_ajax",
    ),
    path(
        "congress-admin/download/delete",
        ajax.admin_delete_download_ajax,
        name="admin_delete_download_ajax",
    ),
    path(
        "congress-admin/move-entry/<int:event_entry_id>",
        congress_admin.admin_move_entry,
        name="admin_move_entry",
    ),
    path(
        "congress-admin/event-entry/notes",
        ajax.admin_event_entry_notes_ajax,
        name="admin_event_entry_notes_ajax",
    ),
    path(
        "congress-admin/event-entry/add/<int:event_id>",
        congress_admin.admin_event_entry_add,
        name="admin_event_entry_add",
    ),
    path(
        "congress-admin/event-entry-player/add/<int:event_entry_id>",
        congress_admin.admin_event_entry_player_add,
        name="admin_event_entry_player_add",
    ),
    path(
        "congress-admin/event-entry-player/delete/<int:event_entry_player_id>",
        congress_admin.admin_event_entry_player_delete,
        name="admin_event_entry_player_delete",
    ),
    path(
        "congress-admin/event-payment-methods/<int:event_id>",
        congress_admin.admin_event_payment_methods,
        name="admin_event_payment_methods",
    ),
    path(
        "congress-admin/event-payment-methods-csv/<int:event_id>",
        congress_admin.admin_event_payment_methods_csv,
        name="admin_event_payment_methods_csv",
    ),
    path(
        "congress-admin/event-entry/change-category",
        congress_admin.admin_event_entry_change_category_htmx,
        name="admin_event_entry_change_category_htmx",
    ),
    path(
        "congress-admin/convener-settings/<int:congress_id>",
        congress_admin.convener_settings,
        name="admin_convener_settings",
    ),
    path(
        "congress-admin/edit-team-name-htmx",
        congress_admin.edit_team_name_htmx,
        name="admin_edit_team_name_htmx",
    ),
    path(
        "congress-admin/congress-finished-with-overdue-payments",
        events.views.congress_admin.congress_finished_with_overdue_payments_htmx,
        name="congress_finished_with_overdue_payments_htmx",
    ),
    path(
        "congress-admin/do-not-automatically-fix-closed-congress",
        events.views.congress_admin.do_not_automatically_fix_closed_congress_htmx,
        name="do_not_automatically_fix_closed_congress_htmx",
    ),
    path(
        "congress-admin/do-automatically-fix-closed-congress",
        events.views.congress_admin.do_automatically_fix_closed_congress_htmx,
        name="do_automatically_fix_closed_congress_htmx",
    ),
    path(
        "congress-admin/fix-closed-congress",
        events.views.congress_admin.fix_closed_congress_htmx,
        name="fix_closed_congress_htmx",
    ),
    #######################################################
    # higher level admin functions                        #
    #######################################################
    path(
        "system-admin/congress-masters",
        events.views.global_admin.global_admin_congress_masters,
        name="global_admin_congress_masters",
    ),
    path(
        "system-admin/congress-master-edit/<int:id>",
        events.views.global_admin.global_admin_edit_congress_master,
        name="global_admin_edit_congress_master",
    ),
    path(
        "system-admin/congress-master-create",
        events.views.global_admin.global_admin_create_congress_master,
        name="global_admin_create_congress_master",
    ),
    path(
        "system-admin/player-view/<int:member_id>",
        events.views.global_admin.global_admin_view_player_entries,
        name="global_admin_view_player_entries",
    ),
    path(
        "system-admin/global-admin-event-payment-health-report",
        events.views.global_admin.global_admin_event_payment_health_report,
        name="global_admin_event_payment_health_report",
    ),
    path(
        "system-admin/events-activity-view",
        events.views.global_admin.events_activity_view,
        name="events_activity_view",
    ),
    path(
        "system-admin/events-activity-view-logs",
        events.views.global_admin.events_activity_view_logs_htmx,
        name="events_activity_view_logs_htmx",
    ),
]
