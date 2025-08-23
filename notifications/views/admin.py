import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.safestring import SafeString
from fcm_django.models import FCMDevice
from post_office import mail as po_email

from accounts.models import User, UnregisteredUser, UserAdditionalInfo
from cobalt.settings import (
    DEFAULT_FROM_EMAIL,
    GLOBAL_TITLE,
)
from masterpoints.views import user_summary
from notifications.models import (
    EmailBatchRBAC,
    BatchID,
    Snooper,
    RealtimeNotificationHeader,
    RealtimeNotification,
)
from notifications.views.aws import aws_remove_email_block
from notifications.views.core import _cloudwatch_reader, send_fcm_message
from organisations.models import MemberClubEmail, MemberClubDetails
from rbac.core import rbac_user_has_role
from rbac.decorators import rbac_check_role
from rbac.views import rbac_forbidden
from utils.utils import cobalt_paginator
from post_office.models import Email as PostOfficeEmail


@login_required()
def admin_view_all_emails(request):
    """Show email notifications for administrators"""

    # check access
    role = "notifications.admin.view"
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    emails = PostOfficeEmail.objects.all().select_related("snooper").order_by("-pk")
    things = cobalt_paginator(request, emails)

    return render(
        request, "notifications/admin_view_all_emails.html", {"things": things}
    )


@login_required()
def admin_view_email_by_batch(request, batch_id):
    """Show an email from a batch"""

    # NOTE: the batch_id parameter passed in is the key to the
    # EmailBatchRBAC table, NOT the key to the BatchID table
    # Prior to April 24 it was being used for both, which only
    # worked because the two were identical in production.
    # This can not be guarenteed.

    batch = get_object_or_404(EmailBatchRBAC, pk=batch_id)

    admin_role = "notifications.admin.view"

    if not (
        rbac_user_has_role(request.user, batch.rbac_role)
        or rbac_user_has_role(request.user, admin_role)
    ):
        return rbac_forbidden(request, batch.rbac_role)

    # snoopers = Snooper.objects.filter(batch_id=batch_id)

    snoopers = Snooper.objects.filter(batch_id=batch.batch_id)

    if not snoopers:
        return HttpResponse("Not found")

    # COB-793
    return render(
        request,
        "notifications/admin_view_email.html",
        {
            "email": snoopers.first().post_office_email,
            "snoopers": snoopers,
            "snooper": snoopers.first(),
        },
    )


@login_required()
def admin_view_email(request, email_id):
    """Show single email for administrators"""

    email = get_object_or_404(PostOfficeEmail, pk=email_id)

    # check access
    snooper = (
        Snooper.objects.select_related("batch_id")
        .filter(post_office_email=email)
        .first()
    )

    admin_role = "notifications.admin.view"

    try:
        rbac_role = (
            EmailBatchRBAC.objects.filter(batch_id=snooper.batch_id).first().rbac_role
        )
    except AttributeError:
        rbac_role = admin_role

    if not (
        rbac_user_has_role(request.user, rbac_role)
        or rbac_user_has_role(request.user, admin_role)
    ):
        return rbac_forbidden(request, rbac_role)

    return render(
        request,
        "notifications/admin_view_email.html",
        {"email": email, "snooper": snooper},
    )


@login_required()
def admin_send_email_copy_to_admin(request, email_id):
    """Send a copy of an email to an admin so they can see it fully rendered

    With using templates for Django post office emails and render_on_delivery,
    we no longer have a copy of the email. We can regenerate it though by
    sending to someone else.

    """

    # check access
    role = "notifications.admin.view"
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    email = get_object_or_404(PostOfficeEmail, pk=email_id)

    # DEFAULT_FROM_EMAIL could be 'a@b.com' or 'something something<a@b.com>'
    if DEFAULT_FROM_EMAIL.find("<") >= 0:
        parts = DEFAULT_FROM_EMAIL.split("<")
        from_name = f"Email Copy from {GLOBAL_TITLE}<{parts[1]}"
    else:
        from_name = f"Email Copy from {GLOBAL_TITLE}<{DEFAULT_FROM_EMAIL}>"

    # We don't send this through the normal method
    po_email.send(
        request.user.email,
        from_name,
        template=email.template,
        context=email.context,
        render_on_delivery=True,
        priority="now",
    )

    return HttpResponse("Message sent. Check your inbox.")


@rbac_check_role("notifications.realtime_send.edit")
def admin_view_realtime_notifications(request):
    """Allow an admin to see their notifications

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    notification_headers = RealtimeNotificationHeader.objects.filter(
        admin=request.user
    ).order_by("-pk")
    things = cobalt_paginator(request, notification_headers)

    return render(request, "notifications/admin_view_realtime.html", {"things": things})


@rbac_check_role("notifications.admin.view")
def global_admin_view_realtime_notifications(request):
    """Allow a global admin to see all real time notifications

    Args:
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """
    notification_headers = RealtimeNotificationHeader.objects.order_by("-pk")
    things = cobalt_paginator(request, notification_headers)

    return render(request, "notifications/admin_view_realtime.html", {"things": things})


@rbac_check_role("notifications.realtime_send.edit", "notifications.admin.view")
def admin_view_realtime_notification_detail(request, header_id):
    """Show the detail of a batch of messages. Actually allows anyone with
       notifications.realtime_send.edit to see any batch, but that is okay.

    Args:
        request (HTTPRequest): standard request object
        header_id (int): id of the RealtimeNotificationHeader to show

    Returns:
        HTTPResponse
    """
    notification_header = get_object_or_404(RealtimeNotificationHeader, pk=header_id)

    # Convert string to json
    notification_header.uncontactable_users = (
        notification_header.get_uncontactable_users()
    )
    notification_header.unregistered_users = (
        notification_header.get_unregistered_users()
    )
    notification_header.invalid_lines = notification_header.get_invalid_lines()

    notifications = RealtimeNotification.objects.filter(
        header=notification_header
    ).select_related("member")

    # Get sent by FCM

    return render(
        request,
        "notifications/admin_view_realtime_detail.html",
        {"notification_header": notification_header, "notifications": notifications},
    )


@rbac_check_role("notifications.realtime_send.edit", "notifications.admin.view")
def admin_view_realtime_notification_item(request, notification_id):
    """Show the detail of a single message. Actually allows anyone with
       notifications.realtime_send.edit to see the message, but that is okay.

    Args:
        request (HTTPRequest): standard request object
        notification_id (int): id of the RealtimeNotification to show

    Returns:
        HTTPResponse
    """
    notification = get_object_or_404(RealtimeNotification, pk=notification_id)

    if notification.fcm_device:
        return _admin_view_realtime_notification_item_fcm(request, notification)
    else:
        return _admin_view_realtime_notification_item_sms(request, notification)


def _admin_view_realtime_notification_item_sms(request, notification):
    """Sub to handle specifics of SMS.

       For SMS we save the AWS Message Id when we send the message, this looks in the
       AWS Cloudwatch logs to find out what happened subsequently.

    Args:
        request (HTTPRequest): standard request object
        notification (RealtimeNotification): RealtimeNotification to show

    Returns:
        HTTPResponse
    """

    # TODO: Move this to a global variable
    success_log_group = "sns/ap-southeast-2/730536189139/DirectPublishToPhoneNumber"
    error_log_group = (
        "sns/ap-southeast-2/730536189139/DirectPublishToPhoneNumber/Failure"
    )

    success_results = _cloudwatch_reader(success_log_group, notification)

    if success_results:
        results = success_results
        successful = True
    else:  # Try for errors, format is the same
        results = _cloudwatch_reader(error_log_group, notification)
        successful = False

    if results:
        message = results[0]["message"]
        message_json = json.loads(message)
        delivery = message_json["delivery"]
        cloudwatch = SafeString(f"<pre>{json.dumps(delivery, indent=4)}</pre>")
        provider_response = delivery["providerResponse"]
    else:
        cloudwatch = "No data found"
        provider_response = "No data found"

    raw_cloudwatch = SafeString(f"<pre>{json.dumps(results, indent=4)}</pre>")

    return render(
        request,
        "notifications/admin_view_realtime_item.html",
        {
            "notification": notification,
            "provider_response": provider_response,
            "cloudwatch": cloudwatch,
            "raw_cloudwatch": raw_cloudwatch,
            "successful": successful,
        },
    )


def _admin_view_realtime_notification_item_fcm(request, notification):
    """Sub to handle specifics of FCM.

    Args:
        request (HTTPRequest): standard request object
        notification (RealtimeNotification): RealtimeNotification to show

    Returns:
        HTTPResponse
    """

    return render(
        request,
        "notifications/admin_view_realtime_item.html",
        {
            "notification": notification,
        },
    )


@rbac_check_role("notifications.admin.view")
def global_admin_view_emails(request, member_id):
    """Allow an admin to see emails for a player

    Args:
        member_id: member to look up
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    member = get_object_or_404(User, pk=member_id)
    summary = user_summary(member.system_number)

    one_year_ago = timezone.now() - timedelta(days=365)

    # emails are indexed by created date, so this may help performance
    last_year_email = PostOfficeEmail.objects.filter(created__gte=one_year_ago)

    email_list = last_year_email.filter(to=[member.email]).order_by("-pk")[:50]

    # email_list = PostOfficeEmail.objects.filter(to=[member.email]).order_by("-pk")[:50]

    return render(
        request,
        "notifications/global_admin_view_emails.html",
        {
            "profile": member,
            "summary": summary,
            "emails": email_list,
        },
    )


@rbac_check_role("notifications.admin.view", "notifications.realtime_send.edit")
def global_admin_view_real_time_for_user(request, member_id):
    """Allow an admin to see real time notifications for a player

    Args:
        member_id: member to look up
        request (HTTPRequest): standard request object

    Returns:
        HTTPResponse
    """

    member = get_object_or_404(User, pk=member_id)
    summary = user_summary(member.system_number)

    real_time_list = RealtimeNotification.objects.filter(member=member).order_by(
        "-created_time"
    )

    return render(
        request,
        "notifications/global_admin_view_real_time_for_user.html",
        {
            "profile": member,
            "summary": summary,
            "real_time_list": real_time_list,
        },
    )


def notifications_status_summary():
    """Used by utils status to get a status of notifications"""

    latest = PostOfficeEmail.objects.all().order_by("-id").first()
    pending = PostOfficeEmail.objects.filter(status=2).count()

    last_hour_date_time = timezone.now() - timedelta(hours=1)

    last_hour = PostOfficeEmail.objects.filter(created__gt=last_hour_date_time).count()

    return {"latest": latest, "pending": pending, "last_hour": last_hour}


@rbac_check_role("system.admin.edit")
def admin_send_test_fcm_message(request):
    """Send a test message to anyone"""

    message = ""

    if request.method == "POST":
        user = User.objects.filter(system_number=request.POST.get("abf")).first()
        msg = request.POST.get("msg")

        try:
            fcm_device = FCMDevice.objects.filter(user=user).latest("pk")
            send_fcm_message(fcm_device, msg, admin=request.user)
            message = f"Message sent to {user} on {fcm_device}"
        except Exception as exc:
            message = exc.__str__()

    return render(
        request, "notifications/admin_send_test_fcm_message.html", {"message": message}
    )


@rbac_check_role("notifications.admin.view")
def unregistered_user_email_admin_htmx(request, message=None):
    """part of unregistered user public profile to allow admins to handle email blocks etc"""

    unreg = get_object_or_404(UnregisteredUser, pk=request.POST.get("user_id"))

    membership_emails = MemberClubEmail.objects.filter(
        system_number=unreg.system_number
    )
    membership_details = MemberClubDetails.objects.filter(
        system_number=unreg.system_number
    )

    return render(
        request,
        "notifications/unregistered_user_email_admin_htmx.html",
        {
            "unreg": unreg,
            "membership_emails": membership_emails,
            "membership_details": membership_details,
            "message": message,
        },
    )


@rbac_check_role("notifications.admin.view")
def unregistered_user_email_admin_remove_block_htmx(request):
    """part of unregistered user public profile to allow admins to handle email blocks etc.
    This removes the block (or at least attempts to) and returns the htmx fragment to show
    the user email details.
    """

    email = request.POST.get("email")

    message = aws_remove_email_block(email)

    return unregistered_user_email_admin_htmx(request, message=message)


@rbac_check_role("notifications.admin.view")
def registered_user_email_admin_remove_block_htmx(request):
    """part of registered user public profile to allow admins to handle email blocks etc.
    This removes the block (or at least attempts to) and returns the htmx fragment to show
    the user email details.
    """

    user_id = request.POST.get("user_id")
    user = get_object_or_404(User, pk=user_id)
    additional = UserAdditionalInfo.objects.filter(user=user).first()
    if additional:
        additional.email_hard_bounce = False
        additional.email_hard_bounce_date = None
        additional.email_hard_bounce_reason = None
        additional.save()

    message = aws_remove_email_block(user.email)

    return HttpResponse(
        f"<h4>Email block removed. Response from AWS was '{message}'</h4>"
    )
