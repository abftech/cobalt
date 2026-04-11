"""
Batch command to auto pay membership fees as at today's date
"""

import logging
import sys

from django.db import transaction
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string

from cobalt.settings import (
    BRIDGE_CREDITS,
    GLOBAL_TITLE,
    GLOBAL_ORG,
    COBALT_HOSTNAME,
)
from organisations.club_admin_core import (
    get_auto_pay_memberships_for_club,
    get_clubs_with_auto_pay_memberships,
    _process_membership_payment,
)
from organisations.models import (
    MemberClubDetails,
)
from notifications.models import (
    BatchID,
)
from notifications.views.core import (
    create_rbac_batch_id,
    send_cobalt_email_with_template,
)
from payments.models import (
    OrgPaymentMethod,
)
from rbac.core import (
    rbac_get_users_with_role,
    rbac_user_has_role_exact,
)
from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock


logger = logging.getLogger("cobalt")
today = timezone.now().date()


class Command(BaseCommand):
    help = "Batch command to auto pay membership fees as at today's date"

    def notify_club(
        self,
        club,
        total_collected=None,
        paid_memberships=None,
        failed_memberships=None,
        blocked_memberships=None,
        unreg_memberships=None,
        no_bridge_credits=False,
    ):
        """Send an email to the club notifying them of the results"""

        # get users with the role at the club level only (not global)
        role = f"orgs.members.{club.id}.edit"
        member_editors = [
            editor
            for editor in rbac_get_users_with_role(role)
            if rbac_user_has_role_exact(editor, role)
        ]

        if not member_editors:
            logger.warning(
                f"Unable to send email to club {club}, no member editors found"
            )
            return

        if no_bridge_credits:

            email_body = render_to_string(
                "organisations/club_menu/members/auto_pay_club_email_content_no_bc.html",
                {
                    "club": club,
                    "today": today,
                    "GLOBAL_TITLE": GLOBAL_TITLE,
                    "BRIDGE_CREDITS": BRIDGE_CREDITS,
                },
            )

        else:

            email_body = render_to_string(
                "organisations/club_menu/members/auto_pay_club_email_content.html",
                {
                    "club": club,
                    "total_collected": total_collected,
                    "paid_memberships": paid_memberships,
                    "failed_memberships": failed_memberships,
                    "blocked_memberships": blocked_memberships,
                    "unreg_memberships": unreg_memberships,
                    "today": today,
                    "no_bridge_credits": no_bridge_credits,
                    "GLOBAL_TITLE": GLOBAL_TITLE,
                    "BRIDGE_CREDITS": BRIDGE_CREDITS,
                    "GLOBAL_ORG": GLOBAL_ORG,
                },
            )

        context = {
            "title": f"Membership auto pay transactions for {club.name}",
            "email_body": email_body,
            "box_colour": "#007bff",
        }

        # create batch ID
        batch_id = create_rbac_batch_id(
            rbac_role=f"notifications.orgcomms.{club.id}.edit",
            organisation=club,
            batch_type=BatchID.BATCH_TYPE_COMMS,
            batch_size=len(member_editors),
            description=context["title"],
            complete=True,
        )

        for user in member_editors:

            context["name"] = user.first_name

            send_cobalt_email_with_template(
                to_address=user.email,
                batch_id=batch_id,
                context=context,
            )

    def notify_member(self, club, membership, batch_id):

        base_url = f"https://{COBALT_HOSTNAME}"

        email_body = render_to_string(
            "organisations/club_menu/members/auto_pay_member_email_content.html",
            {
                "club": club,
                "membership": membership,
                "today": today,
                "GLOBAL_TITLE": GLOBAL_TITLE,
                "BRIDGE_CREDITS": BRIDGE_CREDITS,
                "GLOBAL_ORG": GLOBAL_ORG,
                "base_url": base_url,
            },
        )

        context = {
            "title": f"Membership fee payment for {club.name}",
            "name": membership.user_or_unreg.first_name,
            "email_body": email_body,
            "box_colour": "#007bff",
        }

        send_cobalt_email_with_template(
            to_address=membership.user_or_unreg.email,
            batch_id=batch_id,
            context=context,
        )

    def handle(self, *args, **options):

        logger.info("Batch auto pay starting")

        batch = BatchStatus.objects.create(command="auto_pay_batch")
        summary_lines = []

        try:
            # Use a logical lock to ensure that processes are not running on
            # multiple servers. If another job is running simply exit
            auto_pay_lock = CobaltLock("auto_pay", expiry=10)
            if not auto_pay_lock.get_lock():
                logger.info("Batch auto pay already ran or running (locked), exiting")
                sys.exit(0)

            # process club by club
            clubs = get_clubs_with_auto_pay_memberships()

            logger.info(
                f"Batch auto pay found {len(clubs)} clubs with candidate payments"
            )
            summary_lines.append(
                f"Found {len(clubs)} club(s) with auto pay candidates.\n"
            )

            total_paid_all = 0
            total_collected_all = 0
            clubs_with_payments = 0

            for club in clubs:

                logger.info(f"Batch auto pay starting {club.name}")

                memberships = get_auto_pay_memberships_for_club(club)

                if not memberships:
                    logger.warning(f"No auto pay candidates for {club.name}")
                    summary_lines.append(f"{club.name}: no auto pay candidates")
                    continue

                # get the bridge credit payment method for the club (if any)
                club_bc_payment_method = OrgPaymentMethod.objects.filter(
                    organisation=club,
                    payment_method="Bridge Credits",
                    active=True,
                ).last()

                if not club_bc_payment_method:
                    self.notify_club(club, no_bridge_credits=True)
                    logger.info(f"{club.name} is not configured for {BRIDGE_CREDITS}")
                    summary_lines.append(f"{club.name}: no Bridge Credits configured")
                    continue

                # attempt the payments

                paid_memberships = []
                failed_memberships = []
                blocked_memberships = []
                unreg_memberships = []
                total_collected = 0

                # create batch ID for member notifications
                member_batch_id = create_rbac_batch_id(
                    rbac_role=f"notifications.orgcomms.{club.id}.edit",
                    organisation=club,
                    batch_type=BatchID.BATCH_TYPE_COMMS,
                    batch_size=len(
                        memberships
                    ),  # Changed to use len(memberships) for initial size
                    description=f"Membership fee payment for {club.name}",
                    complete=False,
                )

                for membership in memberships:

                    with transaction.atomic():

                        if membership.action_type == "allowed":
                            # attempt the payment

                            success, message = _process_membership_payment(
                                club,
                                True,
                                membership,
                                club_bc_payment_method,
                                f"{club.name} club membership (auto pay)",
                            )

                            if success:
                                membership.save()

                                if (
                                    membership.member_details.latest_membership
                                    == membership
                                ):
                                    # need to update the status on the member details

                                    membership.member_details.membership_status = (
                                        MemberClubDetails.MEMBERSHIP_STATUS_CURRENT
                                    )
                                    membership.member_details.save()

                                paid_memberships.append(membership)
                                total_collected += membership.fee
                                self.notify_member(club, membership, member_batch_id)

                                logger.info(
                                    f"Auto pay successful for {membership.user_or_unreg}"
                                )

                            else:
                                logger.warning(
                                    f"Auto pay failed for {membership.user_or_unreg.system_number} '{message}'"
                                )
                                membership.message = message
                                failed_memberships.append(membership)

                        elif membership.action_type in ["disallowed", "unreg"]:
                            # remove the auto pay date from the membership

                            logger.info(
                                f"Clearing auto pay for {membership.user_or_unreg.system_number} {membership.action_type}"
                            )

                            membership.auto_pay_date = None
                            membership.save()

                            if membership.action_type == "disallowed":
                                blocked_memberships.append(membership)
                            else:
                                unreg_memberships.append(membership)

                # update the members batch, or delete if no emails sent
                if len(paid_memberships) == 0:  # Changed condition
                    member_batch_id.delete()
                else:
                    member_batch_id.batch_size = len(paid_memberships)
                    member_batch_id.state = BatchID.BATCH_STATE_COMPLETE
                    member_batch_id.save()

                self.notify_club(
                    club,
                    total_collected=total_collected,
                    paid_memberships=paid_memberships,
                    failed_memberships=failed_memberships,
                    blocked_memberships=blocked_memberships,
                    unreg_memberships=unreg_memberships,
                )

                logger.info(
                    (
                        f"{club.name} collected {total_collected} Bridge Credits from auto pay, "
                        + f"{len(paid_memberships)} succeeded, {len(failed_memberships)} failed"
                    )
                )

                summary_lines.append(
                    f"{club.name}: {len(paid_memberships)} paid (${total_collected:.2f}), "
                    f"{len(failed_memberships)} failed, {len(blocked_memberships)} blocked, "
                    f"{len(unreg_memberships)} unregistered"
                )
                total_paid_all += len(paid_memberships)
                total_collected_all += total_collected
                if len(paid_memberships) > 0:
                    clubs_with_payments += 1

            summary_lines.append(
                f"\nTotal: {total_paid_all} paid (${total_collected_all:.2f}) across {clubs_with_payments} club(s)"
            )

            # release the lock
            auto_pay_lock.free_lock()
            auto_pay_lock.delete_lock()

        except Exception as e:
            logger.exception("Batch auto pay failed with an unhandled exception")
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("Batch auto pay finished")
