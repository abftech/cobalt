# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import path

import payments.payments_views.admin
import payments.payments_views.orgs
import payments.payments_views.players
from .payments_views import core

app_name = "payments"  # pylint: disable=invalid-name

urlpatterns = [
    path("", payments.payments_views.players.statement, name="payments"),
    path("stripe-webhook", core.stripe_webhook, name="stripe_webhook"),
    path(
        "create-payment-intent", core.stripe_manual_payment_intent, name="paymentintent"
    ),
    path(
        "create-payment-superintent",
        core.stripe_auto_payment_intent,
        name="paymentsuperintent",
    ),
    path(
        "stripe-pending",
        payments.payments_views.admin.stripe_pending,
        name="stripe_pending",
    ),
    path(
        "admin-payments-static",
        payments.payments_views.admin.admin_payments_static,
        name="admin_payments_static",
    ),
    path(
        "admin-payments-static-history",
        payments.payments_views.admin.admin_payments_static_history,
        name="admin_payments_static_history",
    ),
    path(
        "admin-payments-static-org-override",
        payments.payments_views.admin.admin_payments_static_org_override,
        name="admin_payments_static_org_override",
    ),
    path(
        "admin-payments-static-org-override-add",
        payments.payments_views.admin.admin_payments_static_org_override_add,
        name="admin_payments_static_org_override_add",
    ),
    path(
        "admin-payments-static-org-override-delete/<int:item_id>",
        payments.payments_views.admin.admin_payments_static_org_override_delete,
        name="admin_payments_static_org_override_delete",
    ),
    path(
        "admin-view-stripe-transactions",
        payments.payments_views.admin.admin_view_stripe_transactions,
        name="admin_view_stripe_transactions",
    ),
    path(
        "admin-view-stripe-transaction-detail/<int:stripe_transaction_id>",
        payments.payments_views.admin.admin_view_stripe_transaction_detail,
        name="admin_view_stripe_transaction_detail",
    ),
    path(
        "admin-refund-stripe-transaction/<int:stripe_transaction_id>",
        payments.payments_views.admin.admin_refund_stripe_transaction,
        name="admin_refund_stripe_transaction",
    ),
    path(
        "refund-stripe-transaction/<int:stripe_transaction_id>",
        payments.payments_views.players.refund_stripe_transaction,
        name="refund_stripe_transaction",
    ),
    path("statement", payments.payments_views.players.statement, name="statement"),
    path("settlement", payments.payments_views.admin.settlement, name="settlement"),
    path(
        "manual-adjust-member",
        payments.payments_views.admin.manual_adjust_member,
        name="manual_adjust_member",
    ),
    path(
        "manual-adjust-org",
        payments.payments_views.admin.manual_adjust_org,
        name="manual_adjust_org",
    ),
    path(
        "manual-adjust-org/<int:org_id>/<int:default_transaction>",
        payments.payments_views.admin.manual_adjust_org,
        name="manual_adjust_org",
    ),
    path(
        "statement-admin-view/<int:member_id>",
        payments.payments_views.admin.statement_admin_view,
        name="statement_admin_view",
    ),
    path(
        "statement-csv",
        payments.payments_views.players.statement_csv,
        name="statement_csv",
    ),
    path(
        "statement-csv/<int:member_id>",
        payments.payments_views.players.statement_csv,
        name="statement_csv",
    ),
    path(
        "statement-pdf",
        payments.payments_views.players.statement_pdf,
        name="statement_pdf",
    ),
    path(
        "setup-autotopup",
        payments.payments_views.players.setup_autotopup,
        name="setup_autotopup",
    ),
    path(
        "update-auto-amount",
        payments.payments_views.players.update_auto_amount,
        name="update_auto_amount",
    ),
    path(
        "admin-orgs-with-balance",
        payments.payments_views.admin.admin_orgs_with_balance,
        name="admin_orgs_with_balance",
    ),
    path(
        "admin-members-with-balance",
        payments.payments_views.admin.admin_members_with_balance,
        name="admin_members_with_balance",
    ),
    path(
        "admin-members-with-balance-csv",
        payments.payments_views.admin.admin_members_with_balance_csv,
        name="admin_members_with_balance_csv",
    ),
    path(
        "admin-orgs-with-balance-csv",
        payments.payments_views.admin.admin_orgs_with_balance_csv,
        name="admin_orgs_with_balance_csv",
    ),
    path(
        "admin-view-manual-adjustments",
        payments.payments_views.admin.admin_view_manual_adjustments,
        name="admin_view_manual_adjustments",
    ),
    path(
        "member-transfer",
        payments.payments_views.players.member_transfer,
        name="member_transfer",
    ),
    path(
        "manual-topup",
        payments.payments_views.players.manual_topup,
        name="manual_topup",
    ),
    path(
        "cancel-autotopup",
        payments.payments_views.players.cancel_auto_top_up,
        name="cancel_autotopup",
    ),
    path(
        "statement-admin-summary",
        payments.payments_views.admin.statement_admin_summary,
        name="statement_admin_summary",
    ),
    path(
        "statement-org/<int:org_id>/",
        payments.payments_views.orgs.statement_org,
        name="statement_org",
    ),
    path(
        "statement-csv-org/<int:org_id>/",
        payments.payments_views.orgs.statement_csv_org,
        name="statement_csv_org",
    ),
    path(
        "stripe-webpage-confirm/<int:stripe_id>/",
        payments.payments_views.players.stripe_webpage_confirm,
        name="stripe_webpage_confirm",
    ),
    path(
        "stripe-autotopup-confirm",
        payments.payments_views.players.stripe_autotopup_confirm,
        name="stripe_autotopup_confirm",
    ),
    path(
        "stripe-autotopup-off",
        payments.payments_views.players.stripe_autotopup_off,
        name="stripe_autotopup_off",
    ),
    path(
        "statement-org-summary/<int:org_id>/<str:range>",
        payments.payments_views.orgs.statement_org_summary_ajax,
        name="statement_org_summary_ajax",
    ),
    path(
        "member-transfer-org/<int:org_id>",
        payments.payments_views.orgs.member_transfer_org,
        name="member_transfer_org",
    ),
    path(
        "admin-player-payments/<int:member_id>",
        payments.payments_views.admin.admin_player_payments,
        name="admin_player_payments",
    ),
    path(
        "admin-stripe-rec",
        payments.payments_views.admin.admin_stripe_rec,
        name="admin_stripe_rec",
    ),
    path(
        "admin-stripe-rec-download",
        payments.payments_views.admin.admin_stripe_rec_download,
        name="admin_stripe_rec_download",
    ),
    path(
        "admin-stripe-rec-download-member",
        payments.payments_views.admin.admin_stripe_rec_download_member,
        name="admin_stripe_rec_download_member",
    ),
    path(
        "admin-stripe-rec-download-org",
        payments.payments_views.admin.admin_stripe_rec_download_org,
        name="admin_stripe_rec_download_org",
    ),
    path(
        "get-org-fees",
        payments.payments_views.orgs.get_org_fees,
        name="orgs_get_org_fees",
    ),
    path(
        "get-org-fees/<int:org_id>",
        payments.payments_views.orgs.get_org_fees,
        name="orgs_get_org_fees",
    ),
]
