from unittest.mock import MagicMock, patch

import notifications.views.core as notifications_core
from accounts.models import UserAdditionalInfo
from notifications.models import (
    BatchID,
    EmailBatchRBAC,
    InAppNotification,
    Snooper,
    UnregisteredBlockedEmail,
)
from notifications.views.core import (
    _email_address_on_bounce_list,
    _to_address_checker,
    add_in_app_notification,
    club_default_template,
    contact_member,
    create_rbac_batch_id,
    custom_sender,
    get_notifications_statistics,
    remove_email_from_blocked_list,
    send_cobalt_bulk_email,
    send_cobalt_email_preformatted,
    send_cobalt_email_to_system_number,
    send_cobalt_email_with_template,
    send_fcm_message,
    update_context_for_club_default_template,
)
from organisations.models import OrgEmailTemplate
from tests.test_manager import CobaltTestManagerUnit


def _mock_email_send():
    """Return a mock po_email.send return value (a Post Office Email instance)."""
    mock_email = MagicMock()
    mock_email.id = 999
    return mock_email


class NotificationsCoreTests:
    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.alan = manager.alan
        self.betty = manager.betty

    # ------------------------------------------------------------------ #
    # custom_sender
    # ------------------------------------------------------------------ #

    def test_01_custom_sender_none(self):
        result = custom_sender(None)
        self.manager.save_results(
            status=result is None,
            test_name="custom_sender None",
            test_description="Returns None when from_name is None",
            output=f"Got {result!r}",
        )

    def test_02_custom_sender_with_name(self):
        with patch(
            "notifications.views.core.DEFAULT_FROM_EMAIL", "MyABF<noreply@myabf.com.au>"
        ):
            result = custom_sender("Test Club")
        self.manager.save_results(
            status=result == "Test Club<noreply@myabf.com.au>",
            test_name="custom_sender with name",
            test_description="Formats 'Name<email>' string from DEFAULT_FROM_EMAIL",
            output=f"Got {result!r}",
        )

    def test_03_custom_sender_no_angle_brackets(self):
        with patch(
            "notifications.views.core.DEFAULT_FROM_EMAIL", "noreply@myabf.com.au"
        ):
            result = custom_sender("Test Club")
        self.manager.save_results(
            status=result is None,
            test_name="custom_sender no angle brackets in DEFAULT_FROM_EMAIL",
            test_description="Returns None when DEFAULT_FROM_EMAIL has no <email>",
            output=f"Got {result!r}",
        )

    # ------------------------------------------------------------------ #
    # _email_address_on_bounce_list
    # ------------------------------------------------------------------ #

    def test_04_bounce_list_clean_address(self):
        with patch(
            "notifications.views.core.has_club_email_bounced", return_value=False
        ):
            result = _email_address_on_bounce_list("nobody@example-clean.com")
        self.manager.save_results(
            status=result is False,
            test_name="_email_address_on_bounce_list clean address",
            test_description="Returns False for an address not on any bounce list",
            output=f"Got {result!r}",
        )

    def test_05_bounce_list_hard_bounce(self):
        # Use a unique email to avoid collisions — in the test DB multiple users
        # share the same email address, so querying by email can return the wrong record.
        unique_email = "hard_bounce_unique_test@example-bounce.com"
        original_email = self.betty.email
        self.betty.email = unique_email
        self.betty.save()
        user_info, _ = UserAdditionalInfo.objects.get_or_create(user=self.betty)
        user_info.email_hard_bounce = True
        user_info.save()
        with patch(
            "notifications.views.core.has_club_email_bounced", return_value=False
        ):
            result = _email_address_on_bounce_list(unique_email)
        self.betty.email = original_email
        self.betty.save()
        self.manager.save_results(
            status=result is True,
            test_name="_email_address_on_bounce_list hard bounce",
            test_description="Returns True when user has email_hard_bounce=True",
            output=f"Got {result!r}",
        )

    def test_06_bounce_list_club_bounce(self):
        with patch(
            "notifications.views.core.has_club_email_bounced", return_value=True
        ):
            result = _email_address_on_bounce_list("someclub@example.com")
        self.manager.save_results(
            status=result is True,
            test_name="_email_address_on_bounce_list club bounce",
            test_description="Returns True when has_club_email_bounced returns True",
            output=f"Got {result!r}",
        )

    def test_07_bounce_list_unregistered_blocked(self):
        blocked_email = "blocked-unreg@example.com"
        UnregisteredBlockedEmail.objects.create(
            un_registered_user=self.alan, email=blocked_email
        )
        with patch(
            "notifications.views.core.has_club_email_bounced", return_value=False
        ):
            result = _email_address_on_bounce_list(blocked_email)
        self.manager.save_results(
            status=result is True,
            test_name="_email_address_on_bounce_list unregistered blocked",
            test_description="Returns True when email is in UnregisteredBlockedEmail",
            output=f"Got {result!r}",
        )

    # ------------------------------------------------------------------ #
    # _to_address_checker
    # ------------------------------------------------------------------ #

    def test_08_to_address_checker_production(self):
        """In production (DISABLE_PLAYPEN=ON) the address is returned unchanged."""
        with patch("notifications.views.core.DISABLE_PLAYPEN", "ON"):
            result_addr, result_ctx = _to_address_checker(
                "user@real.com", {"email_body": "hello"}
            )
        self.manager.save_results(
            status=result_addr == "user@real.com",
            test_name="_to_address_checker production mode",
            test_description="Returns original address unchanged when DISABLE_PLAYPEN=ON",
            output=f"Got {result_addr!r}",
        )

    def test_09_to_address_checker_playpen_default_everyone(self):
        """In non-prod with EVERYONE email=a@b.com, redirects to SES simulator."""
        mock_everyone = MagicMock()
        mock_everyone.email = "a@b.com"
        with patch("notifications.views.core.DISABLE_PLAYPEN", "OFF"):
            with patch("notifications.views.core.User") as mock_user_model:
                mock_user_model.objects.get.return_value = mock_everyone
                result_addr, _ = _to_address_checker(
                    "real@example.com", {"email_body": "test"}
                )
        self.manager.save_results(
            status=result_addr == "success@simulator.amazonses.com",
            test_name="_to_address_checker playpen with default EVERYONE email",
            test_description="Redirects to SES simulator when EVERYONE email is a@b.com",
            output=f"Got {result_addr!r}",
        )

    def test_10_to_address_checker_playpen_real_everyone(self):
        """In non-prod with real EVERYONE email, redirects to that email."""
        mock_everyone = MagicMock()
        mock_everyone.email = "admin@myabf.com.au"
        with patch("notifications.views.core.DISABLE_PLAYPEN", "OFF"):
            with patch("notifications.views.core.User") as mock_user_model:
                mock_user_model.objects.get.return_value = mock_everyone
                result_addr, _ = _to_address_checker(
                    "real@example.com", {"email_body": "test"}
                )
        self.manager.save_results(
            status=result_addr == "admin@myabf.com.au",
            test_name="_to_address_checker playpen with real EVERYONE email",
            test_description="Redirects to EVERYONE's real email in non-prod",
            output=f"Got {result_addr!r}",
        )

    # ------------------------------------------------------------------ #
    # club_default_template
    # ------------------------------------------------------------------ #

    def test_11_club_default_template_none_when_no_templates(self):
        mock_club = MagicMock()
        with patch("notifications.views.core.OrgEmailTemplate") as mock_ot:
            mock_ot.objects.filter.return_value.all.return_value = []
            result = club_default_template(mock_club)
        self.manager.save_results(
            status=result is None,
            test_name="club_default_template no templates",
            test_description="Returns None when club has no email templates",
            output=f"Got {result!r}",
        )

    def test_12_club_default_template_single_template(self):
        mock_club = MagicMock()
        mock_tmpl = MagicMock(template_name="Results")
        qs = MagicMock()
        qs.__len__ = MagicMock(return_value=1)
        qs.first.return_value = mock_tmpl
        qs.__iter__ = MagicMock(return_value=iter([mock_tmpl]))
        with patch("notifications.views.core.OrgEmailTemplate") as mock_ot:
            mock_ot.objects.filter.return_value.all.return_value = qs
            result = club_default_template(mock_club)
        self.manager.save_results(
            status=result is mock_tmpl,
            test_name="club_default_template single template",
            test_description="Returns the single template when only one exists",
            output=f"Got {result!r}",
        )

    def test_13_club_default_template_picks_default(self):
        mock_club = MagicMock()
        tmpl_default = MagicMock(template_name="Default")
        tmpl_results = MagicMock(template_name="Results")
        tmpl_other = MagicMock(template_name="Invitations")
        templates = [tmpl_default, tmpl_results, tmpl_other]
        qs = MagicMock()
        qs.__len__ = MagicMock(return_value=len(templates))
        qs.__iter__ = MagicMock(return_value=iter(templates))
        with patch("notifications.views.core.OrgEmailTemplate") as mock_ot:
            mock_ot.objects.filter.return_value.all.return_value = qs
            result = club_default_template(mock_club)
        self.manager.save_results(
            status=result is tmpl_default,
            test_name="club_default_template picks 'Default' named template",
            test_description="When multiple templates exist, prefers the one named 'Default'",
            output=f"Got {result!r}",
        )

    def test_14_club_default_template_results_plus_one(self):
        """With Results + one other but no Default, picks the other."""
        mock_club = MagicMock()
        tmpl_results = MagicMock(template_name="Results")
        tmpl_other = MagicMock(template_name="Invitations")
        templates = [tmpl_results, tmpl_other]
        qs = MagicMock()
        qs.__len__ = MagicMock(return_value=len(templates))
        qs.__iter__ = MagicMock(return_value=iter(templates))
        with patch("notifications.views.core.OrgEmailTemplate") as mock_ot:
            mock_ot.objects.filter.return_value.all.return_value = qs
            result = club_default_template(mock_club)
        self.manager.save_results(
            status=result is tmpl_other,
            test_name="club_default_template Results + one other",
            test_description="With Results + one other (no Default), returns the non-Results template",
            output=f"Got {result!r}",
        )

    def test_15_club_default_template_multiple_no_default(self):
        """Multiple templates, no Default, not the Results+one rule → None."""
        mock_club = MagicMock()
        tmpl_a = MagicMock(template_name="Invitations")
        tmpl_b = MagicMock(template_name="AGM")
        templates = [tmpl_a, tmpl_b]
        qs = MagicMock()
        qs.__len__ = MagicMock(return_value=len(templates))
        qs.__iter__ = MagicMock(return_value=iter(templates))
        with patch("notifications.views.core.OrgEmailTemplate") as mock_ot:
            mock_ot.objects.filter.return_value.all.return_value = qs
            result = club_default_template(mock_club)
        self.manager.save_results(
            status=result is None,
            test_name="club_default_template multiple with no Default",
            test_description="Returns None when multiple templates exist and none is 'Default'",
            output=f"Got {result!r}",
        )

    # ------------------------------------------------------------------ #
    # update_context_for_club_default_template
    # ------------------------------------------------------------------ #

    def test_16_update_context_no_template(self):
        mock_club = MagicMock()
        context = {}
        with patch("notifications.views.core.club_default_template", return_value=None):
            result = update_context_for_club_default_template(mock_club, context)
        self.manager.save_results(
            status=result is None and context == {},
            test_name="update_context_for_club_default_template no template",
            test_description="Returns None and leaves context unchanged when no template",
            output=f"result={result!r}, context={context!r}",
        )

    def test_17_update_context_with_template(self):
        mock_club = MagicMock()
        mock_tmpl = MagicMock()
        mock_tmpl.banner.url = "http://example.com/banner.png"
        mock_tmpl.footer = "Club Footer"
        mock_tmpl.box_colour = "#ff0000"
        mock_tmpl.box_font_colour = "#ffffff"
        context = {}
        with patch(
            "notifications.views.core.club_default_template", return_value=mock_tmpl
        ):
            result = update_context_for_club_default_template(mock_club, context)
        self.manager.save_results(
            status=(
                result is mock_tmpl
                and context.get("img_src") == "http://example.com/banner.png"
                and context.get("footer") == "Club Footer"
                and context.get("box_colour") == "#ff0000"
            ),
            test_name="update_context_for_club_default_template applies template",
            test_description="Populates context with banner, footer, colours from template",
            output=f"context={context!r}",
        )

    # ------------------------------------------------------------------ #
    # send_cobalt_email_with_template
    # ------------------------------------------------------------------ #

    def test_18_send_email_with_template_success(self):
        mock_email = _mock_email_send()
        with patch(
            "notifications.views.core._email_address_on_bounce_list", return_value=False
        ):
            with patch(
                "notifications.views.core._to_address_checker",
                side_effect=lambda to_address, context: (to_address, context),
            ):
                with patch.object(
                    notifications_core.po_email, "send", return_value=mock_email
                ):
                    with patch("notifications.views.core.Snooper"):
                        result = send_cobalt_email_with_template(
                            to_address="test@example.com",
                            context={"subject": "Test", "email_body": "body"},
                        )
        self.manager.save_results(
            status=result is True,
            test_name="send_cobalt_email_with_template success",
            test_description="Returns True when email is queued successfully",
            output=f"Got {result!r}",
        )

    def test_19_send_email_with_template_bounce_list(self):
        with patch(
            "notifications.views.core._email_address_on_bounce_list", return_value=True
        ):
            result = send_cobalt_email_with_template(
                to_address="bounced@example.com",
                context={"subject": "Test", "email_body": "body"},
            )
        self.manager.save_results(
            status=result is False,
            test_name="send_cobalt_email_with_template on bounce list",
            test_description="Returns False without sending when address is on bounce list",
            output=f"Got {result!r}",
        )

    def test_20_send_email_with_template_creates_snooper(self):
        """Snooper is instantiated and saved once per email queued."""
        mock_email = _mock_email_send()
        with patch(
            "notifications.views.core._email_address_on_bounce_list", return_value=False
        ):
            with patch(
                "notifications.views.core._to_address_checker",
                side_effect=lambda to_address, context: (to_address, context),
            ):
                with patch.object(
                    notifications_core.po_email, "send", return_value=mock_email
                ):
                    with patch("notifications.views.core.Snooper") as mock_snooper:
                        send_cobalt_email_with_template(
                            to_address="test@example.com",
                            context={"subject": "Test", "email_body": "body"},
                        )
        self.manager.save_results(
            status=mock_snooper.called and mock_snooper.return_value.save.called,
            test_name="send_cobalt_email_with_template creates Snooper record",
            test_description="Snooper is instantiated and .save() is called once per email",
            output=f"Snooper called: {mock_snooper.called}",
        )

    def test_21_send_email_with_template_subject_from_title(self):
        """When context has 'title' but no 'subject', subject is auto-set from title."""
        mock_email = _mock_email_send()
        captured_context = {}

        def capture_send(**kwargs):
            captured_context.update(kwargs.get("context", {}))
            return mock_email

        with patch(
            "notifications.views.core._email_address_on_bounce_list", return_value=False
        ):
            with patch(
                "notifications.views.core._to_address_checker",
                side_effect=lambda to_address, context: (to_address, context),
            ):
                with patch.object(
                    notifications_core.po_email, "send", side_effect=capture_send
                ):
                    with patch("notifications.views.core.Snooper"):
                        send_cobalt_email_with_template(
                            to_address="test@example.com",
                            context={"title": "My Title", "email_body": "body"},
                        )
        self.manager.save_results(
            status="subject" in captured_context,
            test_name="send_cobalt_email_with_template copies title to subject",
            test_description="context['subject'] is set from context['title'] when absent",
            output=f"subject in context: {'subject' in captured_context}",
        )

    # ------------------------------------------------------------------ #
    # send_cobalt_email_preformatted
    # ------------------------------------------------------------------ #

    def test_22_send_email_preformatted_success(self):
        mock_email = _mock_email_send()
        with patch(
            "notifications.views.core._email_address_on_bounce_list", return_value=False
        ):
            with patch(
                "notifications.views.core._to_address_checker",
                side_effect=lambda to_address, context: (to_address, context),
            ):
                with patch.object(
                    notifications_core.po_email, "send", return_value=mock_email
                ):
                    with patch("notifications.views.core.Snooper"):
                        send_cobalt_email_preformatted(
                            to_address="test@example.com",
                            subject="Test Subject",
                            msg="<p>Hello</p>",
                        )
        # No exception = pass; function returns None
        self.manager.save_results(
            status=True,
            test_name="send_cobalt_email_preformatted success",
            test_description="Queues preformatted email without error",
            output="Completed without exception",
        )

    def test_23_send_email_preformatted_bounce_list(self):
        sent = []
        with patch(
            "notifications.views.core._email_address_on_bounce_list", return_value=True
        ):
            with patch.object(
                notifications_core.po_email,
                "send",
                side_effect=lambda **kw: sent.append(1),
            ):
                send_cobalt_email_preformatted(
                    to_address="bounced@example.com",
                    subject="Test",
                    msg="body",
                )
        self.manager.save_results(
            status=len(sent) == 0,
            test_name="send_cobalt_email_preformatted skips bounce list",
            test_description="Does not call po_email.send when address is on bounce list",
            output=f"po_email.send call count: {len(sent)}",
        )

    # ------------------------------------------------------------------ #
    # create_rbac_batch_id
    # ------------------------------------------------------------------ #

    def test_24_create_rbac_batch_id_new(self):
        batch = create_rbac_batch_id(
            rbac_role="testapp.model.1.edit",
            user=self.alan,
            batch_type="ADM",
            description="Test batch",
        )
        rbac_entry = EmailBatchRBAC.objects.filter(batch_id=batch).first()
        self.manager.save_results(
            status=(
                batch is not None
                and batch.batch_type == "ADM"
                and batch.description == "Test batch"
                and rbac_entry is not None
                and rbac_entry.rbac_role == "testapp.model.1.edit"
            ),
            test_name="create_rbac_batch_id creates new batch",
            test_description="Creates BatchID and EmailBatchRBAC with correct values",
            output=f"batch={batch!r}, rbac_role={rbac_entry.rbac_role if rbac_entry else None!r}",
        )

    def test_25_create_rbac_batch_id_existing(self):
        """Passing an existing batch_id returns it unchanged."""
        existing = BatchID()
        existing.create_new()
        existing.batch_type = "ADM"
        existing.state = BatchID.BATCH_STATE_WIP
        existing.save()

        result = create_rbac_batch_id(
            rbac_role="testapp.model.1.edit",
            batch_id=existing,
        )
        self.manager.save_results(
            status=result is existing,
            test_name="create_rbac_batch_id returns existing batch unchanged",
            test_description="When batch_id is provided, returns it without creating a new one",
            output=f"same object: {result is existing}",
        )

    def test_26_create_rbac_batch_id_complete_state(self):
        batch = create_rbac_batch_id(
            rbac_role="testapp.model.1.edit",
            complete=True,
        )
        self.manager.save_results(
            status=batch.state == BatchID.BATCH_STATE_COMPLETE,
            test_name="create_rbac_batch_id complete=True sets state",
            test_description="complete=True creates batch in COMPLETE state",
            output=f"state={batch.state!r}",
        )

    # ------------------------------------------------------------------ #
    # send_cobalt_bulk_email
    # ------------------------------------------------------------------ #

    def test_27_send_cobalt_bulk_email_spawns_thread(self):
        with patch("notifications.views.core.Thread") as mock_thread:
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance
            send_cobalt_bulk_email(["a@b.com", "c@d.com"], "Subject", "Message")
        self.manager.save_results(
            status=mock_thread.called and mock_instance.start.called,
            test_name="send_cobalt_bulk_email spawns daemon thread",
            test_description="Creates and starts a background thread for bulk sending",
            output=f"Thread created: {mock_thread.called}, started: {mock_instance.start.called}",
        )

    # ------------------------------------------------------------------ #
    # add_in_app_notification
    # ------------------------------------------------------------------ #

    def test_28_add_in_app_notification(self):
        before = InAppNotification.objects.filter(member=self.alan).count()
        add_in_app_notification(self.alan, "Test notification", "/dashboard")
        after = InAppNotification.objects.filter(member=self.alan).count()
        self.manager.save_results(
            status=after == before + 1,
            test_name="add_in_app_notification creates record",
            test_description="Creates an InAppNotification record for the member",
            output=f"Before: {before}, After: {after}",
        )

    def test_29_add_in_app_notification_truncates_long_message(self):
        long_msg = "x" * 150
        add_in_app_notification(self.alan, long_msg)
        notif = (
            InAppNotification.objects.filter(member=self.alan).order_by("-id").first()
        )
        self.manager.save_results(
            status=len(notif.message) <= 100,
            test_name="add_in_app_notification truncates to 100 chars",
            test_description="Message is stored truncated to the 100-char field limit",
            output=f"Stored length: {len(notif.message)}",
        )

    # ------------------------------------------------------------------ #
    # contact_member
    # ------------------------------------------------------------------ #

    def test_30_contact_member_email(self):
        sent = []
        with patch("notifications.views.core.add_in_app_notification"):
            with patch(
                "notifications.views.core.send_cobalt_email_with_template",
                side_effect=lambda **kw: sent.append(kw),
            ):
                contact_member(
                    member=self.alan,
                    msg="Hello",
                    subject="Test subject",
                    link="/dashboard",
                )
        self.manager.save_results(
            status=len(sent) == 1 and sent[0]["to_address"] == self.alan.email,
            test_name="contact_member sends email",
            test_description="Calls send_cobalt_email_with_template with member's email",
            output=f"Call count: {len(sent)}, to_address: {sent[0]['to_address'] if sent else None!r}",
        )

    def test_31_contact_member_sms_raises(self):
        try:
            with patch("notifications.views.core.add_in_app_notification"):
                contact_member(self.alan, "msg", contact_type="SMS")
            raised = False
        except PermissionError:
            raised = True
        self.manager.save_results(
            status=raised,
            test_name="contact_member SMS raises PermissionError",
            test_description="contact_type='SMS' raises PermissionError (SMS removed)",
            output=f"raised={raised}",
        )

    def test_32_contact_member_ignores_system_accounts(self):
        """RBAC_EVERYONE and TBA_PLAYER should be silently ignored."""
        from cobalt.settings import RBAC_EVERYONE
        from accounts.models import User as UserModel

        everyone = UserModel.objects.get(pk=RBAC_EVERYONE)
        sent = []
        with patch(
            "notifications.views.core.send_cobalt_email_with_template",
            side_effect=lambda **kw: sent.append(1),
        ):
            with patch("notifications.views.core.add_in_app_notification"):
                contact_member(everyone, "msg")
        self.manager.save_results(
            status=len(sent) == 0,
            test_name="contact_member ignores system accounts",
            test_description="Does nothing when member is RBAC_EVERYONE or TBA_PLAYER",
            output=f"Send call count: {len(sent)}",
        )

    # ------------------------------------------------------------------ #
    # send_fcm_message
    # ------------------------------------------------------------------ #

    def test_33_send_fcm_message_success(self):
        """Returns True when send_message returns a SendResponse instance."""

        class FakeSendResponse:
            pass

        mock_device = MagicMock()
        mock_device.user = self.alan
        mock_device.send_message.return_value = FakeSendResponse()

        with patch("notifications.views.core.firebase_admin") as mock_firebase:
            mock_firebase.messaging.SendResponse = FakeSendResponse
            with patch("notifications.views.core.RealtimeNotification"):
                result = send_fcm_message(mock_device, "Test push", admin=self.alan)

        self.manager.save_results(
            status=result is True,
            test_name="send_fcm_message success",
            test_description="Returns True when FCM send_message returns SendResponse",
            output=f"Got {result!r}",
        )

    def test_34_send_fcm_message_exception(self):
        """Returns False and doesn't crash when send_message raises an exception."""
        mock_device = MagicMock()
        mock_device.user = self.alan
        mock_device.send_message.side_effect = Exception("FCM connection error")

        with patch("notifications.views.core.RealtimeNotification"):
            result = send_fcm_message(mock_device, "Test push", admin=self.alan)

        self.manager.save_results(
            status=result is False,
            test_name="send_fcm_message exception returns False",
            test_description="Returns False without crashing when FCM raises an exception",
            output=f"Got {result!r}",
        )

    def test_35_send_fcm_message_error_deletes_device(self):
        """When send_message returns a non-SendResponse, device is deleted."""

        class FakeSendResponse:
            pass

        mock_device = MagicMock()
        mock_device.user = self.alan
        mock_device.send_message.return_value = "unexpected_value"  # not SendResponse

        with patch("notifications.views.core.firebase_admin") as mock_firebase:
            mock_firebase.messaging.SendResponse = FakeSendResponse
            with patch("notifications.views.core.RealtimeNotification"):
                result = send_fcm_message(mock_device, "Test push", admin=self.alan)

        self.manager.save_results(
            status=result is False and mock_device.delete.called,
            test_name="send_fcm_message error deletes device",
            test_description="Deletes FCM device and returns False on non-SendResponse result",
            output=f"result={result!r}, device.delete called: {mock_device.delete.called}",
        )

    # ------------------------------------------------------------------ #
    # remove_email_from_blocked_list
    # ------------------------------------------------------------------ #

    def test_36_remove_email_from_blocked_list_registered_user(self):
        user_info, _ = UserAdditionalInfo.objects.get_or_create(user=self.betty)
        user_info.email_hard_bounce = True
        user_info.save()

        with patch("notifications.views.core.clear_club_email_bounced"):
            remove_email_from_blocked_list(self.betty.email)

        user_info.refresh_from_db()
        self.manager.save_results(
            status=user_info.email_hard_bounce is False,
            test_name="remove_email_from_blocked_list clears hard bounce",
            test_description="Sets email_hard_bounce=False for registered user",
            output=f"email_hard_bounce={user_info.email_hard_bounce!r}",
        )

    def test_37_remove_email_from_blocked_list_calls_clear_club(self):
        called = []
        with patch(
            "notifications.views.core.clear_club_email_bounced",
            side_effect=lambda e: called.append(e),
        ):
            remove_email_from_blocked_list("nobody@example.com")
        self.manager.save_results(
            status=len(called) == 1 and called[0] == "nobody@example.com",
            test_name="remove_email_from_blocked_list calls clear_club_email_bounced",
            test_description="Always calls clear_club_email_bounced with the email address",
            output=f"called with: {called!r}",
        )

    # ------------------------------------------------------------------ #
    # get_notifications_statistics
    # ------------------------------------------------------------------ #

    def test_38_get_notifications_statistics_keys(self):
        result = get_notifications_statistics()
        expected_keys = {
            "total_emails",
            "total_real_time_notifications",
            "total_fcm_notifications",
            "total_sms_notifications",
            "total_registered_fcm_devices",
        }
        self.manager.save_results(
            status=isinstance(result, dict) and expected_keys.issubset(result.keys()),
            test_name="get_notifications_statistics returns correct keys",
            test_description="Returns a dict with all expected statistic keys",
            output=f"Keys: {set(result.keys())!r}",
        )

    def test_39_get_notifications_statistics_numeric_values(self):
        result = get_notifications_statistics()
        all_numeric = all(isinstance(v, int) for v in result.values())
        self.manager.save_results(
            status=all_numeric,
            test_name="get_notifications_statistics all values are integers",
            test_description="Every value in the statistics dict is an integer",
            output=f"Values: {result!r}",
        )

    # ------------------------------------------------------------------ #
    # send_cobalt_email_to_system_number
    # ------------------------------------------------------------------ #

    def test_40_send_email_to_system_number_no_email_found(self):
        """When no email address is found for the system number, nothing is sent."""
        sent = []
        with patch(
            "accounts.views.core.get_email_address_and_name_from_system_number",
            return_value=(None, None),
        ):
            with patch(
                "notifications.views.core.send_cobalt_email_with_template",
                side_effect=lambda **kw: sent.append(1),
            ):
                send_cobalt_email_to_system_number(99999, "Subject", "Body")
        self.manager.save_results(
            status=len(sent) == 0,
            test_name="send_cobalt_email_to_system_number no email found",
            test_description="Does not send when get_email_address returns None",
            output=f"Send call count: {len(sent)}",
        )

    def test_41_send_email_to_system_number_with_club(self):
        """When a club is provided, creates a BatchID and sends the email."""
        sent = []
        mock_club = MagicMock()
        mock_club.id = 42

        with patch(
            "accounts.views.core.get_email_address_and_name_from_system_number",
            return_value=("user@example.com", "Alice"),
        ):
            with patch("notifications.views.core.create_rbac_batch_id") as mock_batch:
                mock_batch.return_value = MagicMock()
                with patch(
                    "notifications.views.core.send_cobalt_email_with_template",
                    side_effect=lambda **kw: sent.append(kw),
                ):
                    send_cobalt_email_to_system_number(
                        100, "Subject", "Body", club=mock_club
                    )

        self.manager.save_results(
            status=mock_batch.called and len(sent) == 1,
            test_name="send_cobalt_email_to_system_number with club creates batch",
            test_description="Creates BatchID and sends email when club is provided",
            output=f"batch created: {mock_batch.called}, sent: {len(sent)}",
        )

    def test_42_send_email_to_system_number_without_club(self):
        """Without a club, no BatchID is created."""
        sent = []
        with patch(
            "accounts.views.core.get_email_address_and_name_from_system_number",
            return_value=("user@example.com", "Alice"),
        ):
            with patch("notifications.views.core.create_rbac_batch_id") as mock_batch:
                with patch(
                    "notifications.views.core.send_cobalt_email_with_template",
                    side_effect=lambda **kw: sent.append(kw),
                ):
                    send_cobalt_email_to_system_number(100, "Subject", "Body")
        self.manager.save_results(
            status=not mock_batch.called and len(sent) == 1,
            test_name="send_cobalt_email_to_system_number without club",
            test_description="No BatchID created, email still sent, when no club provided",
            output=f"batch created: {mock_batch.called}, sent: {len(sent)}",
        )
