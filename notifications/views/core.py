import logging
import re
import mimetypes
from datetime import datetime, date
from threading import Thread
from itertools import chain
from urllib.parse import urlencode

# JPG TESTING - to test queue progress
# import time

import boto3
import firebase_admin.messaging
from botocore.exceptions import ClientError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db import connection, IntegrityError
from django.db.models import Count, OuterRef, Subquery, CharField, Q
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from fcm_django.models import FCMDevice
from firebase_admin.messaging import (
    Message,
    Notification,
    AndroidConfig,
    AndroidNotification,
    APNSConfig,
    APNSPayload,
    Aps,
)
from post_office import mail as po_email

from cobalt.settings import MEDIA_ROOT

from accounts.models import User, UserAdditionalInfo, UnregisteredUser
from cobalt.settings import (
    COBALT_HOSTNAME,
    DISABLE_PLAYPEN,
    RBAC_EVERYONE,
    DEFAULT_FROM_EMAIL,
    GLOBAL_TITLE,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION_NAME,
    TBA_PLAYER,
    ALL_SYSTEM_ACCOUNTS,
    ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS,
    apply_large_email_batch_config,
)
from events.models import (
    CongressMaster,
    Congress,
    Event,
    EventEntryPlayer,
)

from notifications.forms import (
    EmailContactForm,
    EmailOptionsForm,
    EmailContentForm,
    EmailAttachmentForm,
)
from notifications.models import (
    Snooper,
    BatchID,
    BatchActivity,
    BatchContent,
    BatchAttachment,
    EmailBatchRBAC,
    Email,
    EmailAttachment,
    RealtimeNotificationHeader,
    RealtimeNotification,
    Recipient,
    InAppNotification,
    UnregisteredBlockedEmail,
)
from organisations.club_admin_core import (
    clear_club_email_bounced,
    get_club_contact_list,
    get_club_members,
    get_club_member_list,
    get_member_count,
    get_member_details,
    has_club_email_bounced,
    MEMBERSHIP_STATES_ACTIVE,
    MEMBERSHIP_STATES_DO_NOT_USE,
    MEMBERSHIP_STATES_TERMINAL,
)
from organisations.models import (
    Organisation,
    ClubTag,
    MemberClubTag,
    OrgEmailTemplate,
)
from organisations.decorators import check_club_menu_access
from rbac.core import rbac_user_has_role, rbac_get_users_with_role
from rbac.views import rbac_forbidden

from post_office.models import Email as PostOfficeEmail

logger = logging.getLogger("cobalt")

# Max no of emails to send in a batch
MAX_EMAILS = 45

# Max number of threads
MAX_EMAIL_THREADS = 20

# Artificial id for EVERYONE club tag
EVERYONE_TAG_ID = 9999999

# Artificial id for all contacts club tag
CONTACTS_TAG_ID = 11111111


def _to_address_checker(to_address, context):
    """Check environment to see what the to_address should be. This protects us from sending to
    real users from test environments
    Args:
        to_address(str): email address to verify based upon environment
        context(dict): dict with email_body (hopefully)
    """
    # If DISABLE_PLAYPEN is set, then just return this unmodified, e.g. production
    if DISABLE_PLAYPEN == "ON":
        return to_address, context
    # TODO: Change this to a variable if we ever use anything other than AWS SES
    # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-simulator.html

    safe_address = "success@simulator.amazonses.com"

    # If the everyone user is set to a valid email then we send to that
    # If still set to the default (a@b.com) then we ignore
    everyone = User.objects.get(pk=RBAC_EVERYONE)

    if everyone.email == "a@b.com":
        return_address = safe_address

        if "email_body" in context:
            context[
                "email_body"
            ] = f"""<h1>Non-production environment<h1>
                                        <h2>This email was not sent</h2>
                                        <h3>To send this in future, update the email address of EVERYONE
                                        from a@b.com to a real email address.</h3>
                                        {context["email_body"]}
                                     """
        logger.warning(
            f"DISABLE_PLAYPEN is OFF. Overriding email address from '{to_address}' to '{return_address}' "
            f"We will use the email address of the EVERYONE user if it is not set to a@b.com."
        )
    else:
        return_address = everyone.email
        logger.warning(
            f"DISABLE_PLAYPEN is OFF. Overriding email address from '{to_address}' to '{return_address}'"
        )
    return return_address, context


def _email_address_on_bounce_list(to_address):
    """Check if we are not sending to this address"""

    # First check if it bounced
    user_additional_info = UserAdditionalInfo.objects.filter(
        user__email=to_address
    ).first()

    club_email_bounced = has_club_email_bounced(to_address)

    if (
        user_additional_info and user_additional_info.email_hard_bounce
    ) or club_email_bounced:
        logger.info(f"Not sending email to suppressed address - {to_address}")
        return True

    # Now check for unregistered users blocking sending
    if UnregisteredBlockedEmail.objects.filter(email=to_address).exists():
        logger.info(f"Not sending email to unregistered user at address - {to_address}")
        return True

    return False


def custom_sender(from_name):
    """Returns a sender address string of the form "from_name<default_email_addres>" or None
    The default email address is picked up from settings (eg "MyABF<donotreply@myabf.com.au>")
    """
    if not from_name:
        return None

    match = re.search(r"<([^<>]+)>", DEFAULT_FROM_EMAIL)
    if match:
        return f"{from_name}<{match.group(1)}>"
    else:
        return None


def club_default_template(club):
    """Determine a reasonable default email template for the club, or None

    This uses the following rules:
    0. If there are no club templates return None
    1. If there is only one club template, regardless of name, use it (ie could be "Results")
    2. If there is one called "Default" use it, regardless of what others exist
    3. If there is no "Default", but "Results" and one other, use the other
    4. If there is more than one and no "Default" (and not case 3) return None
    """
    org_templates = OrgEmailTemplate.objects.filter(organisation=club).all()

    default_template = None

    if len(org_templates) == 0:
        # no club templates (rule 0)
        return None
    elif len(org_templates) == 1:
        # only one template, use it (rule 1)
        default_template = org_templates.first()
    else:
        # more than one template, so see what we have
        named_default = None
        named_results = None
        other_names = []
        for org_template in org_templates:
            if org_template.template_name.upper() == "RESULTS":
                named_results = org_template
            elif org_template.template_name.upper() == "DEFAULT":
                named_default = org_template
            else:
                other_names.append(org_template)
        if named_default:
            # there is a "Default" so use it (rule 2)
            default_template = named_default
        elif named_results and len(other_names) == 1:
            # there is a "Results" and only one other, so use the other (rule 3)
            default_template = other_names[0]

    return default_template


def update_context_for_club_default_template(club, context):
    """Update the context dictionary with club default styling

    Returns the OrgEmailTemplate objected used or None"""

    default_template = club_default_template(club)

    if default_template:
        # update the context

        if default_template.banner:
            context["img_src"] = default_template.banner.url

        if default_template.footer:
            context["footer"] = default_template.footer

        if default_template.box_colour:
            context["box_colour"] = default_template.box_colour

        if default_template.box_font_colour:
            context["box_font_colour"] = default_template.box_font_colour

    return default_template


def send_cobalt_email_with_template(
    to_address,
    context,
    template="system - default flex",
    sender=None,
    priority="medium",
    batch_id=None,
    reply_to=None,
    attachments=None,
    batch_size=1,
    apply_default_template_for_club=None,
    show_club_footer=True,
):
    """Queue an email using a template and context.

    Args:
        to_address (str or list): who to send to  (JPG Comment - does not appear to support list)
        context (dict): values to substitute into email template
        template (str or EmailTemplate instance): it is more efficient to use an instance for multiple calls
        sender (str): who to send from (None will use default from settings file)
        priority (str): Django Post Office priority
        batch_id (BatchID): batch_id for this batch of emails
        reply_to (str): email address to send replies to
        attachments (dict): optional dictionary of attachments
        apply_default_template_for_club (Organisation): apply style settings from a default template for this club
        show_club_footer (bool): allows caller to hide the footer from any club template being applied

    Returns:
        boolean: True if the message was sent, False otherwise

    Context for the default template can have:

    img_src: logo to override default MyABF logo
    name: Users first name
    title: Goes in title box
    email_body: main part of email
    additional_words: goes after main body
    link: link for button e.g. /dashboard
    link_text: words to go on link button
    link_colour: default, primary, warning, danger, success, info
    box_colour: default, primary, warning, danger, success, info

    unregistered_identifier: will use alternative footer and show link to unregistered user preferences

    """

    # Check if on bounce list
    if _email_address_on_bounce_list(to_address):
        logger.info(f"Ignoring email on bounce list {to_address}")
        return False

    # Augment context
    context["host"] = COBALT_HOSTNAME
    context["show_club_footer"] = show_club_footer

    if apply_default_template_for_club:
        default_org_template = update_context_for_club_default_template(
            apply_default_template_for_club, context
        )
    else:
        default_org_template = None

    if "img_src" not in context:
        context["img_src"] = "notifications/img/myabf-email.png"

    # no need to defaul box colour now - default is in template html
    # if "box_colour" not in context:
    #     context["box_colour"] = "primary"

    # Note - link colour is not used in the template html
    if "link_colour" not in context:
        context["link_colour"] = "primary"

    if "subject" not in context and "title" in context:
        context["subject"] = context["title"]

    # mark subject as safe or characters get changed
    if context["subject"]:
        context["subject"] = mark_safe(context["subject"])

    # Check for playpen - don't send emails to users unless on production or similar
    to_address, context = _to_address_checker(to_address, context)

    # COB-793 - add custom header with batch size
    headers = {"X-Myabf-Batch-Size": batch_size}

    limited_notifications = apply_large_email_batch_config(batch_size)
    if limited_notifications:
        logger.debug(f"Email is part of a large batch of {batch_size}")

    if reply_to:
        headers["Reply-to"] = reply_to
    elif default_org_template and default_org_template.reply_to:
        headers["Reply-to"] = default_org_template.reply_to

    this_sender = sender
    if this_sender is None:
        if default_org_template and default_org_template.from_name:
            # this_sender = f"{default_org_template.from_name}<donotreply@myabf.com.au>"
            this_sender = custom_sender(default_org_template.from_name)

    if "img_src" in context:
        context["inline_banner"] = context["img_src"][0] != "/"
    else:
        context["inline_banner"] = True
        context["img_src"] = "notifications/img/myabf-email.png"

    email = po_email.send(
        sender=this_sender,
        recipients=to_address,
        template=template,
        context=context,
        render_on_delivery=True,
        priority=priority,
        headers=headers,
        attachments=attachments,
    )

    Snooper(
        post_office_email=email,
        batch_id=batch_id,
        limited_notifications=limited_notifications,
    ).save()

    return True


def send_cobalt_email_preformatted(
    to_address,
    subject,
    msg,
    sender=None,
    priority="medium",
    batch_id=None,
    reply_to=None,
):
    """Queue an email that has already been formatted. Does not use a template.

        Generally, you should use a template, but sometimes this is necessary.

    Args:
        to_address (str or list): who to send to
        subject (str): subject line
        msg (str): HTML message
        sender (str): who to send from (None will use default from settings file)
        priority (str): Django Post Office priority
        batch_id (BatchID): batch_id for this batch of emails
        reply_to (str): email address to send replies to

    Returns:
        Nothing
    """

    # Check if on bounce list
    if _email_address_on_bounce_list(to_address):
        return

    headers = {"Reply-to": reply_to} if reply_to else None

    # Check for playpen - don't send emails to users unless on production or similar
    # We are the poor cousin and don't have a dict to send (which would normally hold
    # email body) so we send a cut down one and convert the response
    to_address, return_dict = _to_address_checker(
        to_address=to_address, context={"email_body": msg}
    )
    msg = return_dict["email_body"]

    email = po_email.send(
        recipients=to_address,
        sender=sender,
        subject=subject,
        html_message=msg,
        priority=priority,
        headers=headers,
    )

    Snooper(post_office_email=email, batch_id=batch_id).save()


def create_rbac_batch_id(
    rbac_role: str,
    batch_id: BatchID = None,
    user: User = None,
    organisation: Organisation = None,
    batch_type: str = "UNK",
    batch_size: int = 0,
    description: str = None,
    complete: bool = False,
):
    """Create a new EmailBatchRBAC object to allow an RBAC role to access a batch of emails

    Updated in sprint-48 to add type and description

    Args:
        rbac_role (str): the RBAC role to allow. e.g. "org.orgs.34.view"
        batch_id (BatchID): batch ID, if None a new batch Id will be created
        organisation: Org responsible for sending this
        user: User responsible for sending this
        batch_type: Type of batch (BatchID.BATCH_TYPE)
        description: Email subject line or description

    Returns: BatchID

    """

    if not batch_id:
        batch_id = BatchID()
        batch_id.create_new()
        batch_id.batch_type = batch_type
        batch_id.batch_size = batch_size
        batch_id.description = description if description else None
        batch_id.state = (
            BatchID.BATCH_STATE_COMPLETE if complete else BatchID.BATCH_STATE_WIP
        )
        batch_id.organisation = organisation
        batch_id.save()

        EmailBatchRBAC(
            batch_id=batch_id,
            rbac_role=rbac_role,
            meta_sender=user,
            meta_organisation=organisation,
        ).save()

    return batch_id


def send_cobalt_bulk_email(bcc_addresses, subject, message, reply_to=""):
    """Sends the same message to multiple people.

    Args:
        bcc_addresses (list): who to send to, list of strings
        subject (str): subject line for email
        message (str): message to send in HTML or plain format
        reply_to (str): who to send replies to

    Returns:
        Nothing
    """

    # start thread
    thread = Thread(
        target=send_cobalt_bulk_email_thread,
        args=[bcc_addresses, subject, message, reply_to],
    )
    thread.setDaemon(True)
    thread.start()


def send_cobalt_bulk_email_thread(bcc_addresses, subject, message, reply_to):
    """Send bulk emails. Asynchronous thread

    Args:
        bcc_addresses (list): who to send to, list of strings
        subject (str): subject line for email
        message (str): message to send in HTML or plain format
        reply_to (str): who to send replies to

    Returns:
        Nothing
    """

    plain_message = strip_tags(message)

    # split emails into chunks using an ugly list comprehension stolen from the internet
    # turn [a,b,c,d] into [[a,b],[c,d]]
    # fmt: off
    emails_as_list = [
        bcc_addresses[i * MAX_EMAILS: (i + 1) * MAX_EMAILS]
        for i in range((len(bcc_addresses) + MAX_EMAILS - 1) // MAX_EMAILS)
    ]
    # fmt: on

    for emails in emails_as_list:

        msg = EmailMultiAlternatives(
            subject,
            plain_message,
            to=[],
            bcc=emails,
            from_email=DEFAULT_FROM_EMAIL,
            reply_to=[reply_to],
        )

        msg.attach_alternative(message, "text/html")

        msg.send()

        for email in emails:
            Email(
                subject=subject,
                message=message,
                recipient=email,
                status="Sent",
            ).save()

    # Django creates a new database connection for this thread so close it
    connection.close()


def send_cobalt_bulk_notifications(
    msg_list,
    admin,
    description,
    invalid_lines=None,
    total_file_rows=0,
    sender_identification=None,
):
    """This originally sent messages over SMS, but now we only support FCM.

    Args:
        sender_identification(str): e.g. Compscore licence number to identify the sender
        msg_list(list): list of tuples of system number and message to send (system_number, "message")
        admin(User): administrator responsible for sending these messages
        description(str): Text description of this batch of messages
        invalid_lines(list): list of invalid lines in upload file
        total_file_rows(int): Number of rows in original file

    Returns:
        sent_users(list): Who we think we sent messages to
        unregistered_users(list): list of users who we do not know about
        fcm_users(list): list of users we sent FCM messages to. Users may have multiple devices registered
        un_contactable_users(list): list of users who don't have mobiles or haven't ticked to receive SMS
    """

    unregistered_users = []
    uncontactable_users = []
    sent_users = []

    # For now we just store the users, could change this to store users and devices, for non-blank headers this can be
    # worked out anyway
    fcm_sent_users = []
    fcm_failed_users = []

    # Log this batch
    header = RealtimeNotificationHeader(
        admin=admin,
        description=description,
        attempted_send_number=len(msg_list),
        invalid_lines=invalid_lines,
        total_record_number=total_file_rows,
        sender_identification=sender_identification,
    )
    header.save()

    # load data

    app_users, fcm_lookup = _send_cobalt_bulk_notification_get_data(msg_list)

    # Go through and try to send the messages
    for item in msg_list:
        system_number, msg = item
        # Reformat string
        msg = msg.replace("<br>", "\n")

        fcm_device_list = fcm_lookup.get(system_number)
        if fcm_device_list:
            # If it works for any device, count that as successful
            worked = False

            for index, fcm_device in enumerate(fcm_device_list):
                # Only add the first message to the database
                add_message_to_database = index == 0
                if send_fcm_message(
                    fcm_device, msg, admin, header, add_message_to_database
                ):
                    worked = True

            if worked:
                fcm_sent_users.append(system_number)
            else:
                fcm_failed_users.append(system_number)
                uncontactable_users.append(system_number)

        else:
            unregistered_users.append(system_number)

    # Update header
    header.send_status = bool(sent_users + fcm_sent_users)
    header.successful_send_number = len(sent_users) + len(fcm_sent_users)

    # Save lists as strings using model functions
    header.set_uncontactable_users(uncontactable_users)
    header.set_unregistered_users(unregistered_users)
    header.set_invalid_lines(invalid_lines)
    header.save()

    return sent_users + fcm_sent_users, unregistered_users, uncontactable_users


def _send_cobalt_bulk_notification_get_data(msg_list):
    """sub of send_cobalt_bulk_notifications to load required data"""

    # Get system_numbers as list
    system_numbers = [item[0] for item in msg_list]

    # Get the App users (people set up with FCM)
    app_users = FCMDevice.objects.filter(
        user__system_number__in=system_numbers
    ).select_related("user")

    # create dict of ABF number to FCM, can be multiple devices per person
    fcm_lookup = {}
    for app_user in app_users:
        if app_user.user.system_number not in fcm_lookup:
            fcm_lookup[app_user.user.system_number] = []
        fcm_lookup[app_user.user.system_number].append(app_user)

    return app_users, fcm_lookup


def send_cobalt_sms(
    phone_number, msg, from_name=GLOBAL_TITLE, header=None, member=None
):
    """Send single SMS. This will be replaced with a mobile app later

    Args:
        phone_number (str): who to send to
        msg (str): message to send
        from_name(str): Display name of sender
        header(RealtimeNotificationHeader): parent for this message
        member(User): user for this message

    Returns:
        None
    """

    # from_name must be alpha-numeric or hyphens only, must start and end with alphanumeric, 11 chars max
    if len(from_name) > 11:
        from_name = from_name[:11]

    # replace non alphanumerics with -
    from_name = re.sub("[^0-9a-zA-Z]+", "-", from_name)

    # Check start and end
    if from_name[0] == "-":
        from_name[0] = "A"
    if len(from_name) == 11 and from_name[10] == "-":
        from_name[10] = "A"

    client = boto3.client(
        "sns",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME,
    )

    # Assume the worst
    return_code = False

    try:
        return_values = client.publish(
            PhoneNumber=phone_number,
            Message=msg,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": from_name,
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                },
            },
        )

        if return_values["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return_code = True

    except ClientError:
        logger.exception(f"Couldn't publish message to {phone_number}")

    # Log it
    RealtimeNotification(
        member=member,
        admin=header.admin,
        status=return_code,
        msg=msg,
        header=header,
        aws_message_id=return_values["MessageId"],
    ).save()


def contact_member(
    member,
    msg,
    contact_type="Email",
    link=None,
    link_text="View",
    html_msg=None,
    subject=None,
    batch_id=None,
):
    """Contact member using email or SMS. In practice, always Email.

    This is for simple cases:

    It uses the default template with a link. If you don't provide the link it will lookCommon function for contacting users silly.
    msg = short description to go on the in-app notification
    subject is also used as the title (inside body of email)

    batch_id is an option BatchID object for use when sending entry related emails

    """

    # Ignore system accounts
    if member.id in (RBAC_EVERYONE, TBA_PLAYER):
        return

    if not subject:
        subject = "Notification from My ABF"

    if not html_msg:
        html_msg = msg

    # Always create an in app notification
    add_in_app_notification(member, msg, link)

    if contact_type == "Email":
        context = {
            "name": member.first_name,
            "title": subject,
            "email_body": html_msg,
            "link": link,
            "link_text": link_text,
        }

        send_cobalt_email_with_template(
            to_address=member.email,
            context=context,
            batch_id=batch_id,
            apply_default_template_for_club=batch_id.organisation if batch_id else None,
        )

    if contact_type == "SMS":
        raise PermissionError("SMS not supported any more")


def add_in_app_notification(member, msg, link=None):
    """Add a notification to the menu bar telling a user they have a message"""

    InAppNotification(member=member, message=msg[:100], link=link).save()


@login_required()
def email_contact(request, member_id, event_id):
    """email contact form

    Event parameter added to all allow org template to be applied"""

    member = get_object_or_404(User, pk=member_id)

    form = EmailContactForm(request.POST or None)

    if request.method == "POST":
        title = request.POST["title"]
        message = request.POST["message"].replace("\n", "<br>")
        msg = f"""
                  Email from: {request.user} ({request.user.email})<br><br>
                  <b>{title}</b>
                  <br><br>
                  {message}
        """

        context = {
            "name": member.first_name,
            "title": f"Email from: {request.user.full_name}",
            "email_body": msg,
        }

        event = get_object_or_404(Event, pk=event_id)

        # Create batch id so admins can see this email
        batch_id = create_rbac_batch_id(
            rbac_role=f"events.org.{event.congress.congress_master.org.id}.edit",
            organisation=event.congress.congress_master.org,
            batch_type=BatchID.BATCH_TYPE_ENTRY,
            batch_size=1,
            description=title,
            complete=True,
        )

        send_cobalt_email_with_template(
            to_address=member.email,
            context=context,
            batch_id=batch_id,
            reply_to=request.user.email,
            apply_default_template_for_club=event.congress.congress_master.org,
        )

        messages.success(
            request,
            "Message sent successfully",
            extra_tags="cobalt-message-success",
        )

        redirect_to = request.POST.get("redirect_to", "dashboard:dashboard")
        return redirect(redirect_to)

    return render(
        request, "notifications/email_form.html", {"form": form, "member": member}
    )


def _cloudwatch_reader(log_group, notification):
    """Get data from Cloudwatch"""

    client = boto3.client(
        "logs",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME,
    )

    filter_pattern = f'{{ $.notification.messageId = "{notification.aws_message_id}" }}'

    # TODO: Start and end times need investigated. Probably okay not to use them.
    # start_time = int((datetime.now() - timedelta(hours=240)).timestamp()) * 1000
    # end_time = int((datetime.now() + timedelta(hours=240)).timestamp()) * 1000

    # It is possible to get multiple messages and to need a cursor (nextToken) to get all messages
    # Get first response
    response = client.filter_log_events(
        logGroupName=log_group,
        # startTime=start_time,
        # endTime=end_time,
        filterPattern=filter_pattern,
    )

    results = response["events"]

    # Continue to build results if we got a nextToken
    while "nextToken" in response:
        response = client.filter_log_events(
            logGroupName=log_group,
            # startTime=start_time,
            # endTime=end_time,
            filterPattern=filter_pattern,
            nextToken=response["nextToken"],
        )
        results.extend(response["events"])

    return results


@login_required()
def send_test_fcm_message(request, fcm_device_id):
    """Send a test message to a users registered FCM device"""

    fcm_device = FCMDevice.objects.filter(pk=fcm_device_id).first()

    # Check access
    if fcm_device and (
        fcm_device.user == request.user
        or rbac_user_has_role(member=request.user, role="notifications.admin.view")
    ):
        now = timezone.localtime().strftime("%a %d-%b-%Y %-I:%M")
        now += timezone.localtime().strftime("%p").lower()

        test_msg = (
            f"This is a test message.\n\n"
            f"It was sent to {fcm_device.user}.\n\n"
            f"It was sent by {request.user}.\n\n"
            f"It was sent on {now}."
        )

        send_fcm_message(fcm_device, test_msg, request.user)

        return HttpResponse("Message sent")

    return HttpResponse("Device not found or access denied")


def send_fcm_message(
    fcm_device, msg, admin=None, header=None, add_message_to_database=True
):
    """Send a message to a users registered FCM device"""

    if not admin:
        admin = User.objects.get(pk=RBAC_EVERYONE)

    if add_message_to_database:
        # For people with multiple devices we only add the message to the database once
        RealtimeNotification(
            member=fcm_device.user,
            admin=admin,
            msg=msg,
            header=header,
            fcm_device=fcm_device,
        ).save()

    msg = Message(
        notification=Notification(
            title=f"Message for {fcm_device.user.first_name}", body=msg
        ),
        android=AndroidConfig(
            priority="high",
            notification=AndroidNotification(sound="default", default_sound=True),
        ),
        apns=APNSConfig(
            payload=APNSPayload(
                aps=Aps(sound="default"),
            ),
        ),
    )

    # Try to send the message, handle any error, so we don't break the whole sending group
    try:
        rc = fcm_device.send_message(msg)
    except Exception as exc:
        logger.error(exc.__str__())
        return False

    # log it
    if type(rc) is firebase_admin.messaging.SendResponse:
        logger.info(f"Sent message to {fcm_device.user} on device: {fcm_device.name}")
        return True

    # If we get an error then handle it
    else:
        logger.error(f"Error from FCM for {fcm_device.user} - {rc}")
        logger.error(f"Deleting FCM device {fcm_device.name} for {fcm_device.user}")
        fcm_device.delete()
        return False


def send_cobalt_email_to_system_number(
    system_number, subject, message, club=None, administrator=None
):
    """Generic function to send a simple email to a user or unregistered user

    if we get a club then we will use that to look for club specific email addresses

    Updated for sprint-48 to pass additional header information to BatchID
    Note: all emails sent via this function with a club specified are assumed to
    be of batch_type Admin.
    """

    from accounts.views.core import (
        get_email_address_and_name_from_system_number,
    )

    email_address, first_name = get_email_address_and_name_from_system_number(
        system_number, club
    )
    if not email_address:
        logger.warning(
            f"Unable to send email to {system_number}. No email address found."
        )
        return

    un_registered_user = UnregisteredUser.objects.filter(
        system_number=system_number
    ).first()
    if un_registered_user:
        unregistered_identifier = un_registered_user.identifier
    else:
        unregistered_identifier = None

    context = {
        "box_colour": "#00bcd4",
        "name": first_name,
        "title": subject,
        "email_body": message,
        "img_src": "/static/notifications/img/myabf-email.png",
        "unregistered_identifier": unregistered_identifier,
    }

    if club:
        # Create batch id so admins can see this email
        batch_id = create_rbac_batch_id(
            rbac_role=f"notifications.orgcomms.{club.id}.edit",
            user=administrator,
            organisation=club,
            batch_type=BatchID.BATCH_TYPE_ADMIN,
            batch_size=1,
            description=subject,
            complete=True,
        )
    else:
        batch_id = None

    send_cobalt_email_with_template(
        to_address=email_address,
        context=context,
        batch_id=batch_id,
        template="system - club",
        apply_default_template_for_club=club if club else None,
    )


def remove_email_from_blocked_list(email_address):
    """Remove an email address from our internal list of blocked addresses"""

    users = User.objects.filter(email=email_address)

    for user in users:
        user_additional_info, _ = UserAdditionalInfo.objects.get_or_create(user=user)
        user_additional_info.email_hard_bounce = False
        user_additional_info.email_hard_bounce_reason = None
        user_additional_info.email_hard_bounce_date = None
        user_additional_info.save()

    clear_club_email_bounced(email_address)


def get_notifications_statistics():
    """get stats about notifications. Called by util statistics"""

    total_emails = PostOfficeEmail.objects.count()
    total_real_time_notifications = RealtimeNotification.objects.count()
    total_fcm_notifications = RealtimeNotification.objects.filter(
        fcm_device__isnull=False
    ).count()
    total_sms_notifications = total_real_time_notifications - total_fcm_notifications
    total_registered_fcm_devices = FCMDevice.objects.count()

    return {
        "total_emails": total_emails,
        "total_real_time_notifications": total_real_time_notifications,
        "total_sms_notifications": total_sms_notifications,
        "total_fcm_notifications": total_fcm_notifications,
        "total_registered_fcm_devices": total_registered_fcm_devices,
    }


def _add_user_to_recipients(club, batch, user, initial=True):
    """Add a user to the recipients of a batch.

    Returns a tuple of (number added, message string)

    If the user is already a recipient, set as included"""

    # COB-940 ALL_SYSTEM_ACCOUNTS contains ids not system numbers
    # so use ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS instead
    if user.system_number in ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS:
        return (0, f"{user.full_name} is a system account")

    if not user.is_active or user.deceased:
        return (0, f"{user.full_name} is inactive")

    recipients = Recipient.objects.filter(batch=batch, system_number=user.system_number)

    if recipients.exists():
        recipient = recipients.first()
        if not recipient.include:
            recipient.include = True
            recipient.save()
            return (1, f"{user.full_name} included")
        return (0, f"{user.full_name} already included")
    else:
        recipient = Recipient()
        recipient.create_from_user(batch, user, initial=initial)
        recipient.save()
        return (1, f"{user.full_name} added")


_ADD_RECIPIENT_RESULT_OK = "OK"
_ADD_RECIPIENT_RESULT_SYSTEM_AC = "SYS"
_ADD_RECIPIENT_RESULT_DUPLICATE = "DUP"
_ADD_RECIPIENT_RESULT_INACTIVE = "INA"
_ADD_RECIPIENT_RESULT_NO_EMAIL = "NOE"
_ADD_RECIPIENT_RESULT_NOT_FOUND = "NOF"
_ADD_RECIPIENT_RESULTS = [
    (_ADD_RECIPIENT_RESULT_OK, "added"),
    (_ADD_RECIPIENT_RESULT_SYSTEM_AC, "system accounts"),
    (_ADD_RECIPIENT_RESULT_DUPLICATE, "duplicates"),
    (_ADD_RECIPIENT_RESULT_INACTIVE, "inactive users"),
    (_ADD_RECIPIENT_RESULT_NO_EMAIL, "no email address"),
    (_ADD_RECIPIENT_RESULT_NOT_FOUND, "not found"),
]


def _add_to_recipient_with_system_number(
    batch, club, system_number, current_only=False
):
    """Add a club member or contact to the batch

    Returns:
        A result code
        A user message
    """

    # COB-940 ALL_SYSTEM_ACCOUNTS contains ids not system numbers
    # so use ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS instead
    if system_number in ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS:
        return (_ADD_RECIPIENT_RESULT_SYSTEM_AC, "A system account")

    #  is the system number already a recipient?
    existing = Recipient.objects.filter(
        batch=batch, system_number=system_number
    ).first()

    if existing:
        if existing.include:
            return (_ADD_RECIPIENT_RESULT_DUPLICATE, "Recipient already included")
        else:
            existing.include = True
            existing.save()
            return (_ADD_RECIPIENT_RESULT_OK, "Recipient added")

    member_details = get_member_details(club, system_number)

    if not member_details:
        return (_ADD_RECIPIENT_RESULT_NOT_FOUND, "Recipient not found")

    if not member_details.club_email:
        return (_ADD_RECIPIENT_RESULT_NO_EMAIL, "No club email address available")

    if member_details.membership_status in MEMBERSHIP_STATES_DO_NOT_USE:
        return (
            _ADD_RECIPIENT_RESULT_INACTIVE,
            f"{member_details.first_name} {member_details.last_name} is inactive",
        )

    if (
        current_only
        and member_details.membership_status not in MEMBERSHIP_STATES_ACTIVE
    ):
        return (
            _ADD_RECIPIENT_RESULT_INACTIVE,
            f"{member_details.first_name} {member_details.last_name} is not a current member",
        )

    recipient = Recipient()
    recipient.system_number = system_number
    recipient.batch = batch
    recipient.first_name = member_details.first_name
    recipient.last_name = member_details.last_name
    recipient.email = member_details.club_email
    recipient.include = True
    recipient.initial = False
    recipient.save()
    return (_ADD_RECIPIENT_RESULT_OK, "Recipient added")


@login_required
def compose_club_email(request, club_id):
    """Entry point for starting a new club batch email

    Just create the batchId and then start the composition flow"""

    role = f"notifications.orgcomms.{club_id}.edit"
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    club = get_object_or_404(Organisation, pk=club_id)

    # let anyone with comms access to this org view them
    batch = create_rbac_batch_id(
        rbac_role=f"notifications.orgcomms.{club.id}.edit",
        user=request.user,
        organisation=club,
        batch_type=BatchID.BATCH_TYPE_COMMS,
        description=None,
        complete=False,
    )

    return redirect("notifications:compose_email_recipients", club_id, batch.id)


@login_required
def initiate_admin_multi_email(request, club_id):
    """Entry point for multi congress / event selection view

    Just create the batch record and start the composition process"""

    role = f"events.org.{club_id}.edit"
    if not rbac_user_has_role(request.user, role):
        return rbac_forbidden(request, role)

    org = get_object_or_404(Organisation, pk=club_id)

    # create the batch header
    batch = create_rbac_batch_id(
        f"events.org.{club_id}.edit",
        organisation=org,
        batch_type=BatchID.BATCH_TYPE_MULTI,
        batch_size=0,
        complete=False,
    )

    # go to club menu, comms tab, edit batch
    return redirect("notifications:compose_email_multi_select", club_id, batch.id)


def check_user_has_batch_access(user, batch):
    """Check whether the user has the appropriate RBAC role for the batch

    Returns a tuple of boolean successs and the role checked (None if invalid batch type)
    """

    if (
        batch.batch_type
        in batch.batch_type
        in [
            BatchID.BATCH_TYPE_ADMIN,
            BatchID.BATCH_TYPE_COMMS,
            BatchID.BATCH_TYPE_RESULTS,
        ]
    ):
        role = f"notifications.orgcomms.{batch.organisation.id}.edit"
    elif (
        batch.batch_type
        in batch.batch_type
        in [
            BatchID.BATCH_TYPE_CONGRESS,
            BatchID.BATCH_TYPE_EVENT,
            BatchID.BATCH_TYPE_MULTI,
            BatchID.BATCH_TYPE_ENTRY,
        ]
    ):
        role = f"events.org.{batch.organisation.id}.edit"
    else:
        return (False, None)

    return (rbac_user_has_role(user, role), role)


def check_club_and_batch_access():
    """Decorator to check club and batch email access rights when editing batches

    Expects a request, club_id and batch_id_id.
    Passes request, club and batch to the called function

    Modelled on organisations/decorators.py/check_club_menu_access
    """

    def _method_wrapper(function):
        def _arguments_wrapper(request, club_id, batch_id_id, *args, **kwargs):

            # Test if logged in
            if not request.user.is_authenticated:
                return redirect("/")

            club = get_object_or_404(Organisation, pk=club_id)

            batch = BatchID.objects.filter(pk=batch_id_id).first()
            if not batch:
                messages.error(
                    request,
                    "This batch no longer exists",
                    extra_tags="cobalt-message-error",
                )

                # return redirect("organisations:club_menu", club.id)
                return redirect(
                    "organisations:club_menu_tab_entry_point",
                    club.id,
                    "comms",
                )

            # need to check for comms or congress permissions depending
            # on the batch type being manipulated

            access_granted, role_required = check_user_has_batch_access(
                request.user, batch
            )

            if not access_granted:
                if role_required:
                    return rbac_forbidden(request, role_required)
                else:
                    return HttpResponse("Error - not an editable batch type")

            if batch.state != BatchID.BATCH_STATE_WIP:
                # batch is no longer editable, presumably has been sent by another user

                messages.error(
                    request,
                    "This batch is no longer editable",
                    extra_tags="cobalt-message-error",
                )

                # return redirect("organisations:club_menu", club.id)
                return redirect(
                    "organisations:club_menu_tab_entry_point",
                    club.id,
                    "comms",
                )

            # all ok
            return function(request, club, batch, *args, **kwargs)

        return _arguments_wrapper

    return _method_wrapper


def _batch_has_been_customised(batch):
    """Returns whether a batch has been customised at all

    Used to determine whether to show cancel or delete"""

    # check the batch header information
    if batch.description or batch.template or batch.reply_to or batch.from_name:
        return True

    # check for batch activities
    if BatchActivity.objects.filter(batch=batch).count() > 0:
        return True

    # check for recipients
    if Recipient.objects.filter(batch=batch).count() > 0:
        return True

    # check for batch content
    if BatchContent.objects.filter(batch=batch).count() > 0:
        return True

    # check for attachements
    if BatchAttachment.objects.filter(batch=batch).count() > 0:
        return True

    return False


@check_club_and_batch_access()
def compose_email_multi_select(request, club, batch):
    """Compose batch emails - step 0 - select events (multis only)"""

    # non_draft_congress_count=Count('congress_set', filter=~Q(congress_set__status='Draft'))

    # select masters and count non-draft congresses, exclude any master with no non-draft congresses
    masters = (
        CongressMaster.objects.filter(org=club)
        .annotate(
            non_draft_congress_count=Count(
                "congress",
                filter=Q(congress__status="Published") | Q(congress__status="Closed"),
            )
        )
        .filter(non_draft_congress_count__gt=0)
    )

    if request.method == "POST":
        # update the selected batch activities and rebuild the recipients

        # delete existing activities and recipients
        BatchActivity.objects.filter(batch=batch).delete()

        Recipient.objects.filter(batch=batch).delete()

        # The form will return all selected items in the tree, including components
        # of a higher level item (eg all events within a selected congress), so need
        # to only add activities for the highest level items (eg the congress, not
        # the events). The set of events, however, can be used to select the recipients.

        selected_masters = []
        selected_congresses = []
        selected_events = []
        added_count = 0

        # process masters first (note - cannot trust the order keys are returned)
        for key, value in request.POST.items():
            parts = key.split("-")
            if parts[0] != "master":
                continue
            master = get_object_or_404(CongressMaster, pk=int(value))
            selected_masters.append(master.pk)
            BatchActivity(
                batch=batch,
                activity_id=int(value),
                activity_type=BatchActivity.ACTIVITY_TYPE_SERIES,
            ).save()

        # process congresses, ignoring if part of a selected series
        for key, value in request.POST.items():
            parts = key.split("-")
            if parts[0] != "congress":
                continue
            congress = get_object_or_404(Congress, pk=int(value))
            selected_congresses.append(congress.pk)
            if congress.congress_master.pk not in selected_masters:
                BatchActivity(
                    batch=batch,
                    activity_id=int(value),
                    activity_type=BatchActivity.ACTIVITY_TYPE_CONGRESS,
                ).save()

        # process events, adding an activity if not in a selected congress / master
        # and always adding entrants to recipients
        for key, value in request.POST.items():

            parts = key.split("-")
            if parts[0] != "event":
                continue
            event = get_object_or_404(Event, pk=int(value))
            selected_events.append(event.pk)
            if (
                event.congress.pk not in selected_congresses
                and event.congress.congress_master.pk not in selected_masters
            ):
                BatchActivity(
                    batch=batch,
                    activity_id=int(value),
                    activity_type=BatchActivity.ACTIVITY_TYPE_EVENT,
                ).save()

            # create recipients for the event
            entered_players = (
                EventEntryPlayer.objects.filter(
                    event_entry__event=event,
                    player__is_active=True,
                )
                .exclude(event_entry__entry_status="Cancelled")
                .select_related("player")
            )

            for entered_player in entered_players:
                # COB-940 ALL_SYSTEM_ACCOUNTS contains ids not system numbers
                # so use ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS instead
                if (
                    entered_player.player.system_number
                    not in ALL_SYSTEM_ACCOUNT_SYSTEM_NUMBERS
                ):
                    recipient = Recipient()
                    recipient.create_from_user(batch, entered_player.player)
                    try:
                        recipient.save()
                        added_count += 1
                    except IntegrityError:
                        # ignore duplicate system_numbers within the batch
                        pass

        if added_count > 0:
            # and redirect to the next step

            return redirect("notifications:compose_email_recipients", club.id, batch.id)
        else:
            messages.add_message(request, messages.INFO, "No entrants found")

    else:
        # build the view from the selected batch activities
        # Note that when a branch is selected (eg a series or congress), all elements
        # on that branch must be added (eg if all events for a selected congress)

        selected_masters = []
        selected_congresses = []
        selected_events = []

        activities = BatchActivity.objects.filter(
            batch=batch,
        ).all()

        for activity in activities:

            # add all congresses and events for a series
            if activity.activity_type == BatchActivity.ACTIVITY_TYPE_SERIES:
                master = get_object_or_404(CongressMaster, pk=activity.activity_id)
                selected_masters.append(master.pk)
                for congress in master.congress_set.all():
                    selected_congresses.append(congress.pk)
                    for event in congress.event_set.all():
                        selected_events.append(event.pk)

            if activity.activity_type == BatchActivity.ACTIVITY_TYPE_CONGRESS:
                congress = get_object_or_404(Congress, pk=activity.activity_id)
                selected_congresses.append(congress.pk)
                for event in congress.event_set.all():
                    selected_events.append(event.pk)

            if activity.activity_type == BatchActivity.ACTIVITY_TYPE_EVENT:
                event = get_object_or_404(Event, pk=activity.activity_id)
                selected_events.append(event.pk)

    start_date_str = (
        batch.date_range_from.strftime("%d/%m/%Y") if batch.date_range_from else ""
    )
    end_date_str = (
        batch.date_range_to.strftime("%d/%m/%Y") if batch.date_range_to else ""
    )

    return render(
        request,
        "notifications/batch_email_multi_event.html",
        {
            "step": 0,
            "batch": batch,
            "club": club,
            "cancelable": not _batch_has_been_customised(batch),
            "masters": masters,
            "selected_masters": selected_masters,
            "selected_congresses": selected_congresses,
            "selected_events": selected_events,
            "existing_selection": (
                len(selected_masters) + len(selected_congresses) + len(selected_events)
            )
            > 0,
            "start_date_str": start_date_str,
            "end_date_str": end_date_str,
        },
    )


@check_club_and_batch_access()
def compose_email_multi_select_by_date(request, club, batch):
    """User should have specified a start and end date to select by

    Creates BatchActivities based on date and then redirects to main select view"""

    # get and validate the date range
    start_date_str = request.POST.get("start_date")
    end_date_str = request.POST.get("end_date")

    date_format = "%d/%m/%Y"
    error_msg = None
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, date_format).date()
        else:
            start_date = date(2020, 12, 1)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, date_format).date()
        else:
            end_date = date.today()
    except ValueError:
        error_msg = "Invalid date"

    if error_msg or end_date < start_date:
        # invalid date range. Note message must be added to the request, not the response
        messages.error(
            request,
            error_msg if error_msg else "Invalid date range",
            extra_tags="cobalt-message-error",
        )
        base_url = reverse(
            "notifications:compose_email_multi_select",
            kwargs={
                "club_id": club.id,
                "batch_id_id": batch.id,
            },
        )
        query_params = urlencode(
            {"start_date_str": start_date_str, "end_date_str": end_date_str}
        )
        response = HttpResponse("Redirecting...", status=302)
        response["HX-Redirect"] = f"{base_url}?{query_params}"
        return response

    # save the date range
    batch.date_range_from = start_date
    batch.date_range_to = end_date
    batch.save()

    # delete the existing batch activities
    BatchActivity.objects.filter(batch=batch).delete()

    # build the new set of batch activities
    masters = CongressMaster.objects.filter(org=club)

    total_event_count = 0

    for master in masters:

        selected_congresses = []
        excluded_congresses = []

        for congress in master.congress_set.all():
            if congress.status != "Draft":
                selected_events = []
                excluded_events = []

                # check each of the events in this congress
                for event in congress.event_set.all():

                    # calculate event date range from session dates
                    event_start_date = None
                    event_end_date = None
                    for session in event.session_set.all():
                        if event_start_date is None:
                            event_start_date = session.session_date
                            event_end_date = session.session_date
                        elif session.session_date < event_start_date:
                            event_start_date = session.session_date
                        elif session.session_date > event_end_date:
                            event_end_date = session.session_date

                    if event_start_date >= start_date and event_end_date <= end_date:
                        selected_events.append(event)
                        total_event_count += 1
                    else:
                        excluded_events.append(event)

                if len(excluded_events) == 0:
                    # all events selected (ie none excluded), so include the congress
                    selected_congresses.append(congress)

                else:
                    # count the congress as excluded and create batch activities for the events
                    excluded_congresses.append(congress)

                    # for selected_event in selected_congresses:
                    for selected_event in selected_events:
                        BatchActivity(
                            batch=batch,
                            activity_type=BatchActivity.ACTIVITY_TYPE_EVENT,
                            activity_id=selected_event.id,
                        ).save()

        if len(excluded_congresses) == 0:
            # all congresses in the master selected so create a batch activity for the master

            BatchActivity(
                batch=batch,
                activity_type=BatchActivity.ACTIVITY_TYPE_SERIES,
                activity_id=master.id,
            ).save()

        else:
            # some subset of congresses selected (possibly none), so create congress batch activities

            for selected_congress in selected_congresses:
                BatchActivity(
                    batch=batch,
                    activity_type=BatchActivity.ACTIVITY_TYPE_CONGRESS,
                    activity_id=selected_congress.id,
                ).save()

    # display the new list, with an appropriate message about the results

    if total_event_count == 0:
        messages.warning(
            request,
            f"Nothing selected for the date range {start_date.strftime(date_format)} to {end_date.strftime(date_format)}",
            extra_tags="cobalt-message-warning",
        )
    else:
        messages.info(
            request,
            f"{total_event_count} event{'' if total_event_count == 1 else 's'} selected for the date range {start_date.strftime(date_format)} to {end_date.strftime(date_format)}",
        )

    base_url = reverse(
        "notifications:compose_email_multi_select",
        kwargs={
            "club_id": club.id,
            "batch_id_id": batch.id,
        },
    )
    query_params = urlencode(
        {"start_date_str": start_date_str, "end_date_str": end_date_str}
    )

    response = HttpResponse("Redirecting...", status=302)
    response["HX-Redirect"] = f"{base_url}?{query_params}"
    return response


@check_club_and_batch_access()
def compose_email_multi_clear_date_range_htmx(request, club, batch):
    """Clear the date range stored in the batch
    Called whenever a change is made after a select by date"""

    batch.date_range_from = None
    batch.date_range_to = None
    batch.save()

    # Return a 204 No Content response
    return HttpResponse(status=204)


@check_club_and_batch_access()
def compose_email_recipients(request, club, batch):
    """Compose batch emails - step 1 - review recipients"""

    congress_stream = batch.batch_type in [
        BatchID.BATCH_TYPE_CONGRESS,
        BatchID.BATCH_TYPE_EVENT,
        BatchID.BATCH_TYPE_MULTI,
    ]

    if request.method == "GET":
        try:
            page_number = int(request.GET.get("page"))
        except ValueError:
            page_number = 1
        except TypeError:
            # None passed
            page_number = 1
    else:
        page_number = 1

    # get all of the recients for the batch and paginate
    recipients = Recipient.objects.filter(
        batch=batch,
    ).order_by("initial", "last_name", "first_name")

    recipient_count = recipients.filter(include=True).count()
    if recipient_count != batch.batch_size:
        batch.batch_size = recipient_count
        batch.save()

    page_size = 20
    pages = Paginator(recipients, page_size)
    page = pages.get_page(page_number)

    # work out where the added and initial headers should be placed on the current page

    added_count = Recipient.objects.filter(batch=batch, initial=False).count()
    initial_count = Recipient.objects.filter(batch=batch, initial=True).count()

    if added_count == 0 or initial_count == 0:
        initial_header_before_row = None
        added_header_before_row = None
    else:
        first_row_on_page = (page_number - 1) * page_size + 1
        last_row_on_page = min(
            (initial_count + added_count), first_row_on_page + page_size - 1
        )
        if added_count <= first_row_on_page:
            #  have paged past the beginning of the initial selection, so show a header
            initial_header_before_row = 1
            added_header_before_row = None
        else:
            # top of page is in the added section, so show a header
            added_header_before_row = 1
            if added_count < last_row_on_page:
                initial_header_before_row = added_count - (first_row_on_page - 1) + 1
            else:
                initial_header_before_row = None

    # determine range of pages to show in pagination row

    half_span = 4
    # the number of pages to the left and right if in the middle of a large number of pages
    full_span = half_span * 2 + 1

    if pages.num_pages <= full_span:
        # simple case - able to show all pages at once
        page_range = range(1, pages.num_pages + 1)
    else:
        if page_number <= (half_span + 1):
            # near the beginning
            page_range = range(1, full_span + 1)
        elif page_number >= (pages.num_pages - half_span - 1):
            # near the end
            page_range = range(pages.num_pages - full_span + 1, pages.num_pages + 1)
        else:
            # in the middle
            page_range = range(page_number - half_span, page_number + half_span + 1)

    return render(
        request,
        "notifications/batch_email_recipients.html",
        {
            "step": 1,
            "batch": batch,
            "club": club,
            "cancelable": not _batch_has_been_customised(batch),
            "page": page,
            "page_range": page_range,
            "initial_header_before_row": initial_header_before_row,
            "added_header_before_row": added_header_before_row,
            "congress_stream": congress_stream,
            "recipient_count": recipient_count,
        },
    )


@check_club_and_batch_access()
def compose_email_recipients_add_self(request, club, batch):
    """Add current user to the recipient list"""

    _, feedback = _add_user_to_recipients(club, batch, request.user, initial=False)
    messages.add_message(request, messages.INFO, feedback)

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_add_congress_email(request, club, batch):
    """Add the congress contact email(s) to the recipient list"""

    # build a list of congress email addresses from batch activities
    congress_emails = set()  # set to avoid duplicates
    for activity in batch.activities.all():
        if activity.activity_type == BatchActivity.ACTIVITY_TYPE_CONGRESS:
            congress = get_object_or_404(Congress, pk=activity.activity_id)
            congress_emails.add(congress.contact_email)
        elif activity.activity_type == BatchActivity.ACTIVITY_TYPE_EVENT:
            event = get_object_or_404(Event, pk=activity.activity_id)
            congress_emails.add(event.congress.contact_email)
        elif activity.activity_type == BatchActivity.ACTIVITY_TYPE_SERIES:
            series = get_object_or_404(CongressMaster, pk=activity.activity_id)
            for congress in series.congress_set.all():
                congress_emails.add(congress.contact_email)

    # add the contact emails as recipients
    added_count = 0
    for email in congress_emails:

        already_in = Recipient.objects.filter(email=email)

        if already_in.exists():
            # exists, but make sure that it is included
            recipient = already_in.first()
            if not recipient.include:
                recipient.include = True
                recipient.save()
                added_count += 1
        else:
            # add it
            recipient = Recipient()
            recipient.batch = batch
            recipient.email = email
            recipient.first_name = None
            recipient.last_name = f"Contact Email {email}"
            recipient.system_number = None
            recipient.include = True
            recipient.initial = False
            recipient.save()
            added_count += 1

    if added_count == 0:
        messages.add_message(request, messages.WARNING, "No contact emails added")
    else:
        messages.add_message(
            request,
            messages.INFO,
            f"{added_count} contact email{'s' if added_count > 1 else ''} added",
        )

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_add_tadmins(request, club, batch):
    """Add club tournament organisers to the recipients"""

    tournament_admins = rbac_get_users_with_role(f"events.org.{club.id}.edit")

    added_count = 0

    for td in tournament_admins:
        delta, _ = _add_user_to_recipients(club, batch, td, initial=False)
        added_count += delta

    if added_count == 0:
        messages.add_message(request, messages.WARNING, "No tournament admins added")
    else:
        messages.add_message(
            request,
            messages.INFO,
            f"{added_count} tournament admin{'s' if added_count > 1 else ''} added",
        )

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


def _updated_recipient_count(request, batch):
    """Return an HTML snippet with te updated recipent count for the batch"""

    recipient_count = Recipient.objects.filter(
        batch=batch,
        include=True,
    ).count()

    if recipient_count != batch.batch_size:
        batch.batch_size = recipient_count
        batch.save()

    return HttpResponse(
        f"{recipient_count if recipient_count else 'No'} recipient{'' if recipient_count == 1 else 's'}"
    )


@login_required()
def compose_email_recipients_toggle_recipient_htmx(request, recipient_id):
    """Toggle the include state of the recipient"""

    recipient = get_object_or_404(Recipient, pk=recipient_id)

    # check access
    access_granted, role_required = check_user_has_batch_access(
        request.user, recipient.batch
    )
    if not access_granted:
        return rbac_forbidden(request, role_required, htmx=True)

    recipient.include = not recipient.include
    recipient.save()

    # return HttpResponse(status=204)
    return _updated_recipient_count(request, recipient.batch)


@check_club_and_batch_access()
def compose_email_recipients_select_all(request, club, batch):
    """Include all current recipients"""

    Recipient.objects.filter(batch=batch, include=False).update(include=True)

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_deselect_all(request, club, batch):
    """Deselect all current recipients"""

    Recipient.objects.filter(batch=batch, include=True).update(include=False)

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_remove_unselected_htmx(request, club, batch):
    """Remove all unselected recipients from a batch"""

    Recipient.objects.filter(batch=batch, include=False).delete()

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_tags_pane_htmx(request, club, batch):
    """Display the club tags pane in the add recipient view

    Note: This code generates counts of members by tag, regardless of
    whether the member has an email (either as a User or and UnregisteredUser
    with a club email). This could confuse users, eg adding a tag with N members
    but having less than N recipients added to the list.
    """

    total_members = get_member_count(club)

    if total_members:
        club_tags = (
            ClubTag.objects.filter(organisation=club)
            .annotate(member_count=Count("memberclubtag"))
            .order_by("tag_name")
        )
        tags = [(EVERYONE_TAG_ID, "Everyone", total_members)] + [
            (tag.id, tag.tag_name, tag.member_count) for tag in club_tags.all()
        ]
    else:
        # no point listing the tags if there are no members
        tags = []

    return render(
        request,
        "notifications/batch_email_recipients_tags_htmx.html",
        {
            "club": club,
            "batch": batch,
            "tags": tags,
        },
    )


@check_club_and_batch_access()
def compose_email_recipients_member_search_htmx(request, club, batch):
    """Returns a list of club member and contact search candidates

    Searches by first name, last name or system number (not a combination)
    Matches on the start of the relevent field, and can include members
    with no club email address (unregistered users).

    Such unregsistered users will be shown in the UI without a link.
    It may be less confusing if a known member is on the list but
    not selectable, rather than not there at all.
    """

    first_name_search = request.POST.get("member-search-first", "")
    last_name_search = request.POST.get("member-search-last", "")
    system_number_search = request.POST.get("member-search-number", "")

    # if there is nothing to search for, don't search
    if not first_name_search and not last_name_search and not system_number_search:
        return HttpResponse("")

    member_details = get_club_members(club, exclude_contacts=False, active_only=False)

    if first_name_search and not last_name_search:
        first_name_search_upper = first_name_search.upper()
        members = [
            member
            for member in member_details
            if member.first_name.upper().startswith(first_name_search_upper)
        ]
    elif last_name_search and not first_name_search:
        last_name_search_upper = last_name_search.upper()
        members = [
            member
            for member in member_details
            if member.last_name.upper().startswith(last_name_search_upper)
        ]
    elif first_name_search and last_name_search:
        first_name_search_upper = first_name_search.upper()
        last_name_search_upper = last_name_search.upper()
        members = [
            member
            for member in member_details
            if member.first_name.upper().startswith(first_name_search_upper)
            and member.last_name.upper().startswith(last_name_search_upper)
        ]
    else:
        members = [
            member
            for member in member_details
            if not member.internal
            and str(member.system_number).startswith(system_number_search)
        ]

    return render(
        request,
        "notifications/batch_email_recipients_member_search_htmx.html",
        {
            "club": club,
            "batch": batch,
            "members": members,
            "inactive_states": MEMBERSHIP_STATES_TERMINAL,
        },
    )


@check_club_and_batch_access()
def compose_email_recipients_add_tag(request, club, batch, tag_id):
    """Add recipients from a club tag"""

    reason_counts = {reason_code: 0 for (reason_code, _) in _ADD_RECIPIENT_RESULTS}

    if tag_id in [EVERYONE_TAG_ID, CONTACTS_TAG_ID]:
        #  add all members

        if tag_id == EVERYONE_TAG_ID:
            system_numbers = get_club_member_list(club)
        else:
            system_numbers = get_club_contact_list(club)

        for system_number in system_numbers:
            result, _ = _add_to_recipient_with_system_number(batch, club, system_number)
            reason_counts[result] += 1

    else:
        # add from a real club tag

        tag = get_object_or_404(ClubTag, pk=tag_id)
        tag_members = MemberClubTag.objects.filter(club_tag=tag)
        for mct in tag_members:
            result, _ = _add_to_recipient_with_system_number(
                batch, club, mct.system_number
            )
            reason_counts[result] += 1

    msg = f"{reason_counts[_ADD_RECIPIENT_RESULT_OK]} recipient{'s' if reason_counts[_ADD_RECIPIENT_RESULT_OK] != 1 else ''} added"

    excluded_count = 0
    excluded_msg = ""
    for excluded_reason, excluded_desc in _ADD_RECIPIENT_RESULTS[1:]:
        if reason_counts[excluded_reason]:
            excluded_count += reason_counts[excluded_reason]
            excluded_msg += f"{reason_counts[excluded_reason]} {excluded_desc}, "
    if excluded_count:
        msg += f" ({excluded_count} not added: {excluded_msg[:-2]})"

    messages.add_message(
        request,
        messages.INFO,
        msg,
    )

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_add_member(request, club, batch, system_number):
    """Add a club member by system number as a recipient"""

    _, feedback = _add_to_recipient_with_system_number(batch, club, system_number)

    messages.add_message(request, messages.INFO, feedback)

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_recipients_remove_tag(request, club, batch, tag_id, from_all):
    """Remove tagged club members from a batch's recipients
    Either from all recipeinets, or from added (ie not initial) recipients only"""

    if tag_id == EVERYONE_TAG_ID:
        system_numbers = get_club_member_list(club)

    else:
        tag = get_object_or_404(ClubTag, pk=tag_id)
        source = MemberClubTag.objects.filter(club_tag=tag)
        system_numbers = [item.system_number for item in source.all()]

    if from_all:
        # un-include all occurances

        Recipient.objects.filter(
            batch=batch, system_number__in=system_numbers, include=True
        ).update(include=False)

    else:
        # only un-include from non-initial recipients

        Recipient.objects.filter(
            batch=batch, system_number__in=system_numbers, include=True, initial=False
        ).update(include=False)

    messages.add_message(
        request,
        messages.INFO,
        f"{'EVERYONE' if tag_id == EVERYONE_TAG_ID else tag.tag_name} removed",
    )

    return redirect("notifications:compose_email_recipients", club.id, batch.id)


@check_club_and_batch_access()
def compose_email_options(request, club, batch):
    """Compose batch emails - step 2 - email options"""

    if request.method == "POST":

        email_options_form = EmailOptionsForm(request.POST, club=club)

        if email_options_form.is_valid():

            # When a template is selected it populates the other two fields
            # from the template. These values can be changed and would then override
            # the template values. Rather than implement complex logic to determine
            # whether the values are being overridden, just save the values as provided.

            if email_options_form.cleaned_data.get("template"):
                selected_template_id = email_options_form.cleaned_data.get("template")
                if selected_template_id != 0:
                    template = get_object_or_404(
                        OrgEmailTemplate, pk=selected_template_id
                    )
                else:
                    template = None
            else:
                template = None
                selected_template_id = None
            batch.template = template
            batch.reply_to = email_options_form.cleaned_data.get("reply_to")
            batch.from_name = email_options_form.cleaned_data.get("from_name")
            batch.save()

            #  proceed to step 3 - content
            return redirect("notifications:compose_email_content", club.id, batch.id)

    else:
        email_options_form = EmailOptionsForm(club=club)

        if batch.template:
            # use the stored template, but override the template value for the other two fields
            selected_template_id = batch.template.id

            email_options_form.fields["from_name"].initial = batch.from_name
            email_options_form.fields["reply_to"].initial = batch.reply_to
        elif len(email_options_form.fields["template"].choices) > 0:
            # first time through

            # apply the rules for determining a default
            # (could return None even if there are templates defined)
            org_default_template = club_default_template(club)

            if org_default_template:
                selected_template_id = org_default_template.id
            else:
                # use the first one, unless it is RESULTS and there is another option

                selected_template_id = email_options_form.fields["template"].choices[0][
                    0
                ]
                if (
                    email_options_form.fields["template"].choices[0][1].upper()
                    == "RESULTS"
                ):
                    if len(email_options_form.fields["template"].choices) > 1:
                        selected_template_id = email_options_form.fields[
                            "template"
                        ].choices[1][0]

            template = get_object_or_404(OrgEmailTemplate, pk=selected_template_id)
            email_options_form.fields["from_name"].initial = template.from_name
            email_options_form.fields["reply_to"].initial = template.reply_to
            # save these to the batch
            batch.template = template
            batch.from_name = template.from_name
            batch.reply_to = template.reply_to
            batch.save()
        else:
            # no templates so just use defaults
            selected_template_id = None
            email_options_form.fields["from_name"].initial = batch.from_name
            email_options_form.fields["reply_to"].initial = batch.reply_to

    return render(
        request,
        "notifications/batch_email_options.html",
        {
            "selected_template_id": selected_template_id,
            "step": 2,
            "batch": batch,
            "club": club,
            "cancelable": not _batch_has_been_customised(batch),
            "email_options_form": email_options_form,
        },
    )


@check_club_and_batch_access()
def compose_email_options_from_and_reply_to_htmx(request, club, batch):
    """Rebuild the from and reply_to fields in the send email form if the template changes"""

    template_id = request.POST.get("template")

    template = get_object_or_404(OrgEmailTemplate, pk=template_id)

    email_options_form = EmailOptionsForm(club=club)

    email_options_form.fields["from_name"].initial = template.from_name
    email_options_form.fields["reply_to"].initial = template.reply_to

    # save these to the batch
    batch.template = template
    batch.from_name = template.from_name
    batch.reply_to = template.reply_to
    batch.save()

    return render(
        request,
        "notifications/batch_email_options_from_and_reply_to_htmx.html",
        {"batch": batch, "club": club, "email_options_form": email_options_form},
    )


@check_club_and_batch_access()
def compose_email_content(request, club, batch):
    """Compose batch emails - step 1 - review recipients"""

    ready_to_send = False

    if request.method == "POST":

        email_content_form = EmailContentForm(request.POST)

        if email_content_form.is_valid():

            if hasattr(batch, "batchcontent"):
                batch.batchcontent.email_body = email_content_form.cleaned_data.get(
                    "email_body", ""
                )
                batch.batchcontent.save()
            else:
                new_content = BatchContent()
                new_content.batch = batch
                new_content.email_body = email_content_form.cleaned_data.get(
                    "email_body", ""
                )
                new_content.save()

            if email_content_form.cleaned_data.get("subject"):
                batch.description = email_content_form.cleaned_data.get(
                    "subject", "Batch email"
                )
                batch.save()

            ready_to_send = True
            pass

    else:

        email_content_form = EmailContentForm()
        email_content_form.fields["subject"].initial = batch.description

        if hasattr(batch, "batchcontent"):
            email_content_form.fields["email_body"].initial = (
                batch.batchcontent.email_body
            )
            ready_to_send = True

    return render(
        request,
        "notifications/batch_email_content.html",
        {
            "step": 3,
            "batch": batch,
            "club": club,
            "cancelable": not _batch_has_been_customised(batch),
            "email_content_form": email_content_form,
            "ready_to_send": ready_to_send,
        },
    )


@check_club_and_batch_access()
def compose_email_content_preview_htmx(request, club, batch):
    """Show a preview of the emails in the batch in a separate window"""

    context = {
        "host": COBALT_HOSTNAME,
        "batch": batch,
        "name": "Member",
        "subject": batch.description,
    }

    # determine the html template and title values based on the batch type
    if batch.batch_type in [
        BatchID.BATCH_TYPE_CONGRESS,
        BatchID.BATCH_TYPE_EVENT,
    ]:

        context["po_template_name"] = "two_headings"
        context["po_template_html_name"] = "po_email_with_two_headings_flex.html"
        activity = BatchActivity.objects.filter(batch=batch).first()
        if activity.activity_type == BatchActivity.ACTIVITY_TYPE_CONGRESS:
            congress = get_object_or_404(Congress, pk=activity.activity_id)
        else:
            event = get_object_or_404(Event, pk=activity.activity_id)
            congress = event.congress
        context["title1"] = (
            f"Message from {request.user.full_name} on behalf of {congress}"
        )
        context["title2"] = batch.description

    elif batch.batch_type in [
        BatchID.BATCH_TYPE_MULTI,
    ]:

        context["po_template_name"] = "two_headings"
        context["po_template_html_name"] = "po_email_with_two_headings_flex.html"
        context["title1"] = f"Message from {request.user.full_name} on behalf of {club}"
        context["title2"] = batch.description

    elif batch.batch_type in [
        BatchID.BATCH_TYPE_COMMS,
        BatchID.BATCH_TYPE_RESULTS,
    ]:

        context["po_template_name"] = "club"
        context["po_template_html_name"] = "po_club_template.html"
        context["title"] = batch.description

    else:

        context["po_template_name"] = "defaults"
        context["po_template_html_name"] = "po_email_default_flex.html"
        context["title"] = batch.description

    batch_content = get_object_or_404(BatchContent, batch=batch)
    context["email_body"] = batch_content.email_body

    if batch.template:
        org_template = batch.template
    else:
        org_template = club_default_template(club) or OrgEmailTemplate(
            organisation=club
        )

    context["img_src"] = org_template.banner.url
    context["box_colour"] = org_template.box_colour
    context["box_font_colour"] = org_template.box_font_colour
    context["footer"] = org_template.footer
    context["from_name"] = org_template.from_name
    context["reply_to"] = org_template.reply_to

    context["attachment_objects"] = EmailAttachment.objects.filter(batches__batch=batch)

    # host
    # img_src
    # box_colour
    # box_font_colour
    # subject
    # email_body

    return render(
        request,
        "notifications/batch_email_content_preview_htmx.html",
        context,
    )


@check_club_and_batch_access()
def compose_email_content_send_htmx(request, club, batch):
    """Handle sending a test message or the full batch

    Redirects to one of the process steps if there is an issue, otherwise
    redirects to the watch email view.
    """

    (ok_to_send, error_message, rectification_step) = _validate_batch_details(batch)

    if ok_to_send:
        (attachments, attachment_size) = _attachment_dict_for_batch(batch)

        if attachment_size > 10_000_000:
            (ok_to_send, error_message, rectification_step) = (
                False,
                "Attachments are too large",
                3,
            )

    if ok_to_send:

        dispatched = _dispatch_batch(
            request,
            club,
            batch,
            attachments,
            test_user=request.user if "test" in request.POST else None,
        )

        if dispatched:
            if "test" in request.POST and request.POST["test"] == "test":
                messages.success(
                    request,
                    f"Test message sent to {request.user.email}",
                    extra_tags="cobalt-message-success",
                )

                return HttpResponse(f"Test message sent to {request.user.email}")
            else:
                # redirect to email watch view
                # is this really useful for very samll batches (eg 1-4 recipients)

                response = HttpResponse("Redirecting...", status=302)

                # response["HX-Redirect"] = reverse(
                #     "notifications:watch_emails", kwargs={"batch_id": batch.batch_id}
                # )

                response["HX-Redirect"] = reverse(
                    "organisations:club_menu_tab_entry_point",
                    kwargs={"club_id": club.id, "tab_name": "comms"},
                )
                return response
        else:
            (ok_to_send, error_message, rectification_step) = (
                False,
                "Unable to send",
                3,
            )

    messages.error(
        request,
        error_message,
        extra_tags="cobalt-message-error",
    )

    response = HttpResponse("Redirecting...", status=302)

    if rectification_step == 1:
        response["HX-Redirect"] = reverse(
            "notifications:compose_email_recipients",
            kwargs={"club_id": club.id, "batch_id": batch.id},
        )
    elif rectification_step == 2:
        response["HX-Redirect"] = reverse(
            "notifications:compose_email_options",
            kwargs={"club_id": club.id, "batch_id": batch.id},
        )
    else:
        response["HX-Redirect"] = reverse(
            "notifications:compose_email_content",
            kwargs={"club_id": club.id, "batch_id": batch.id},
        )

    return response


def _attachment_dict_for_batch(batch):
    """Returns an attachment dictionary and total attachment size (bytes)"""

    attachment_ids = BatchAttachment.objects.filter(batch=batch).values_list(
        "attachment_id", flat=True
    )
    attachment_id_list = list(attachment_ids)
    attachments = {}
    total_size = 0.0
    if len(attachment_id_list) > 0:
        attachments_objects = EmailAttachment.objects.filter(id__in=attachment_id_list)
        for attachments_object in attachments_objects:
            mime_type, _ = mimetypes.guess_type(attachments_object.filename())
            if mime_type is None:
                attachments[attachments_object.filename()] = (
                    attachments_object.attachment.path
                )
            else:
                attachments[attachments_object.filename()] = {
                    "file": attachments_object.attachment.path,
                    "mimetype": mime_type,
                }
            total_size += attachments_object.attachment.size
    return (attachments, total_size)


def _validate_batch_details(batch):
    """Check whether the batch is really ready to send

    Returns a tuple of:
        Success (Trie/False)
        User error message
        Process step to rectify (1,2, 3)
    """

    if batch.state != BatchID.BATCH_STATE_WIP:
        return (False, "Batch has already been sent")

    if len(batch.description) == 0:
        return (False, "Please specify a subject")

    recipient_count = Recipient.objects.filter(batch=batch, include=True).count()

    if recipient_count == 0:
        return (False, "Batch has no recipients")

    return (True, None, None)


def _dispatch_batch(request, club, batch, attachments, test_user=None):
    """Queue a batch of emails to be sent

    If a test_user is specified the email is only sent to that user.

    Returns success (true/false)
    """

    # get the recipients
    if test_user:
        recipients = [test_user]
    else:
        recipients = Recipient.objects.filter(
            batch=batch,
            include=True,
        )

    # build the template rendering context
    context = {
        "subject": batch.description,
    }

    if hasattr(batch, "batchcontent"):
        context["email_body"] = batch.batchcontent.email_body

    if batch.template:
        org_template = batch.template
    else:
        org_template = club_default_template(club) or OrgEmailTemplate(
            organisation=club
        )

    if org_template.banner:
        context["img_src"] = org_template.banner.url

    if org_template.footer:
        context["footer"] = org_template.footer
    if org_template.box_colour:
        context["box_colour"] = org_template.box_colour
    if org_template.box_font_colour:
        context["box_font_colour"] = org_template.box_font_colour

    # determine which EmailTemplate to use, and update context with
    # and template specific parameters

    if batch.batch_type in [
        BatchID.BATCH_TYPE_CONGRESS,
        BatchID.BATCH_TYPE_EVENT,
    ]:

        po_template = "system - two headings flex"
        activity = BatchActivity.objects.filter(batch=batch).first()
        if activity.activity_type == BatchActivity.ACTIVITY_TYPE_CONGRESS:
            congress = get_object_or_404(Congress, pk=activity.activity_id)
        else:
            event = get_object_or_404(Event, pk=activity.activity_id)
            congress = event.congress
        context["title1"] = (
            f"Message from {request.user.full_name} on behalf of {congress}"
        )
        context["title2"] = batch.description

    elif batch.batch_type in [
        BatchID.BATCH_TYPE_MULTI,
    ]:

        po_template = "system - two headings flex"
        context["title1"] = f"Message from {request.user.full_name} on behalf of {club}"
        context["title2"] = batch.description

    elif batch.batch_type in [
        BatchID.BATCH_TYPE_COMMS,
        BatchID.BATCH_TYPE_RESULTS,
    ]:

        po_template = "system - club"
        context["title"] = batch.description

    else:

        context["title"] = batch.description
        po_template = "system - default flex"

    # other arguements required to send the email

    # from_name = batch.from_name  # where is this used ?
    reply_to = batch.reply_to

    if len(recipients) == 1:

        context["name"] = recipients[0].first_name
        # sender = f"{batch.from_name}<donotreply@myabf.com.au>" if batch.from_name else None
        sender = custom_sender(batch.from_name)

        send_cobalt_email_with_template(
            to_address=recipients[0].email,
            context=context,
            template=po_template,
            batch_id=None if test_user else batch,
            reply_to=reply_to,
            sender=sender,
            attachments=attachments if len(attachments) > 0 else None,
            batch_size=1,
        )

        if test_user is None:
            _finalise_email_batch(batch, batch_size=1)

    else:
        # send in a separate thread

        # start thread
        thread = Thread(
            target=_dispatch_batch_thread,
            args=[
                batch,
                recipients,
                context,
                po_template,
                reply_to,
                attachments,
            ],
        )
        thread.setDaemon(True)
        thread.start()

    return True


def _dispatch_batch_thread(
    batch,
    recipients,
    context,
    po_template,
    reply_to,
    attachments,
):
    """Asynchronous thread to send bulk emails for a batch"""

    # Mark the batch as in flight
    batch.state = BatchID.BATCH_STATE_IN_FLIGHT
    batch.batch_size = len(recipients)
    batch.save()

    # sender = f"{batch.from_name}<donotreply@myabf.com.au>" if batch.from_name else None
    sender = custom_sender(batch.from_name)

    try:
        for recipient in recipients:

            # JPG TESTING - to test queuing progress
            # time.sleep(3)

            context["name"] = recipient.first_name

            send_cobalt_email_with_template(
                to_address=recipient.email,
                context=context,
                template=po_template,
                batch_id=batch,
                reply_to=reply_to,
                sender=sender,
                attachments=attachments if len(attachments) > 0 else None,
                batch_size=batch.batch_size,
            )

            logger.info(
                f"Queued email to {recipient.first_name} {recipient.last_name}, {recipient.email}"
            )
    except Exception as e:
        # something went wrong, so mark the batch as errored and reraise the exception
        batch.state = BatchID.BATCH_STATE_ERRORED
        batch.save()
        logger.error(f"Error queuing email batch, Exception {e}")
        raise

    _finalise_email_batch(batch)


@check_club_and_batch_access()
def compose_email_content_attachment_htmx(request, club, batch):
    """Handle the attachments pane"""

    email_attachments = EmailAttachment.objects.filter(organisation=club).order_by(
        "-pk"
    )[:50]

    # Add hx_vars for the delete function
    for email_attachment in email_attachments:
        email_attachment.hx_vars = (
            f"club_id:{club.id},email_attachment_id:{email_attachment.id}"
        )
        email_attachment.modal_id = f"del_attachment{email_attachment.id}"

    return render(
        request,
        "notifications//batch_email_content_email_attachment_htmx.html",
        {"club": club, "batch": batch, "email_attachments": email_attachments},
    )


@check_club_and_batch_access()
def compose_email_content_upload_new_email_attachment_htmx(request, club, batch):
    """Upload a new email attachment for a club
    Use the HTMX hx-trigger response header to tell the browser about it
    """

    form = EmailAttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        email_attachment = form.save(commit=False)
        email_attachment.organisation = club
        email_attachment.save()

        trigger = f"""{{"post_attachment_add":{{"id": "{email_attachment.id}" , "name": "{email_attachment.filename()}"}}}}"""

        return _email_attachment_list_htmx(
            request, club, batch, hx_trigger_response=trigger
        )

    return HttpResponse("Error")


def _email_attachment_list_htmx(request, club, batch, hx_trigger_response=None):
    """Shows just the list of attachments, called if we delete or add an attachment"""

    email_attachments = EmailAttachment.objects.filter(organisation=club).order_by(
        "-pk"
    )[:50]

    # Add hx_vars for the delete function
    for email_attachment in email_attachments:
        email_attachment.hx_vars = (
            f"club_id:{club.id},email_attachment_id:{email_attachment.id}"
        )
        email_attachment.modal_id = f"del_attachment{email_attachment.id}"

    # For delete we need to trigger a response in the browser to remove this from the list (if present)
    # We use the hx_trigger response header for this

    response = render(
        request,
        "notifications/batch_email_content_email_attachments_list_htmx.html",
        {"club": club, "batch": batch, "email_attachments": email_attachments},
    )

    if hx_trigger_response:
        response["HX-Trigger"] = hx_trigger_response

    return response


@check_club_and_batch_access()
def compose_email_content_include_attachment_htmx(request, club, batch, attachment_id):
    """Include an attachment in the email

    Save to the model and return the list of included attachments"""

    attachment = get_object_or_404(EmailAttachment, pk=attachment_id)

    existing = BatchAttachment.objects.filter(
        batch=batch, attachment=attachment
    ).first()

    if not existing:
        batch_attachment = BatchAttachment()
        batch_attachment.batch = batch
        batch_attachment.attachment = attachment
        batch_attachment.save()

    return _compose_email_content_included_attachments_htmx(request, club, batch)


@check_club_and_batch_access()
def compose_email_content_remove_attachment_htmx(
    request, club, batch, batch_attachment_id
):
    """Remove a batch attachment from the email

    Update the model and return the list of included attachments"""

    batch_attachment = get_object_or_404(BatchAttachment, pk=batch_attachment_id)

    batch_attachment.delete()

    return _compose_email_content_included_attachments_htmx(request, club, batch)


@check_club_and_batch_access()
def compose_email_content_included_attachments_htmx(request, club, batch):
    """Return the list of included attachments (ie batch attachments)"""

    return _compose_email_content_included_attachments_htmx(request, club, batch)


def _compose_email_content_included_attachments_htmx(request, club, batch):
    """Return the list of included attachments (ie batch attachments)"""

    batch_attachments = BatchAttachment.objects.filter(batch=batch)

    return render(
        request,
        "notifications/batch_email_content_included_attachments_htmx.html",
        {
            "batch": batch,
            "club": club,
            "batch_attachments": batch_attachments,
        },
    )


def _finalise_email_batch(batch, batch_size=None):
    """Clean-up processing once a batch has been sent"""

    if batch_size is not None:
        batch.batch_size = batch_size

    batch.created = timezone.now()
    batch.state = BatchID.BATCH_STATE_COMPLETE
    batch.save()

    if hasattr(batch, "batchcontent"):
        BatchContent.objects.filter(batch=batch).delete()

    Recipient.objects.filter(batch=batch).delete()

    BatchAttachment.objects.filter(batch=batch).delete()


@check_club_and_batch_access()
def delete_email_batch(request, club, batch):
    """Delete an incomplete batch"""

    batch.delete()

    return redirect(
        "organisations:club_menu_tab_entry_point", batch.organisation.id, "comms"
    )


def batch_queue_progress_htmx(request, batch_id_id):
    """Return an HTML fragment with the batches queuing progress"""

    def _final_response(msg, refresh=True):
        response = HttpResponse(msg, status=286)
        response["HX-Refresh"] = "true"
        return response

    if not request.user.is_authenticated:
        return redirect("/")

    batch = BatchID.objects.filter(pk=batch_id_id).first()

    if not batch:
        # batch has been deleted by someone?
        return _final_response("Deleted")

    if batch.state != BatchID.BATCH_STATE_IN_FLIGHT:
        # batch is no longer in flight
        return _final_response("All queued")

    if batch.batch_size == 0:
        return HttpResponse("Unknown", status=286)

    queued = (
        Snooper.objects.select_related("post_office_email")
        .filter(batch_id=batch)
        .count()
    )

    if queued == batch.batch_size:
        return _final_response("All queued")
    else:
        return HttpResponse(f"{queued / batch.batch_size:.0%} queued")


def get_emails_sent_to_address(email_address, club, viewing_user, slice=20):
    """
    Return a list of Post Office Email objects sent to the specified email address.

    Only emails relevant to the club are returned, and only those that the viewing
    user has access rights to read.

    Returns the most recent <slice> emails, or None
    """

    if not email_address:
        return []

    if rbac_user_has_role(
        viewing_user, "notifications.admin.view"
    ) or rbac_user_has_role(viewing_user, "orgs.admin.edit"):

        # user has global access so return all recent emails
        post_office_emails = PostOfficeEmail.objects.filter(
            to=[email_address]
        ).order_by("-pk")[:slice]

    else:

        # check relevant user access
        comms_access = rbac_user_has_role(
            viewing_user, f"notifications.orgcomms.{club.id}.edit"
        )
        congress_access = rbac_user_has_role(viewing_user, f"events.org.{club.id}.edit")
        if not congress_access:
            congress_access = rbac_user_has_role(
                viewing_user, f"events.org.{club.id}.view"
            )

        if comms_access or congress_access:

            # build a list of permitted batch types to view for this user
            if comms_access:
                permitted_batch_types = [
                    BatchID.BATCH_TYPE_ADMIN,
                    BatchID.BATCH_TYPE_COMMS,
                    BatchID.BATCH_TYPE_RESULTS,
                ]

            else:
                permitted_batch_types = []

            if congress_access:
                permitted_batch_types += [
                    BatchID.BATCH_TYPE_CONGRESS,
                    BatchID.BATCH_TYPE_EVENT,
                    BatchID.BATCH_TYPE_MULTI,
                    BatchID.BATCH_TYPE_ENTRY,
                ]

            # Query PostOfficeEmail objects through the reverse relation from Snooper
            post_office_emails = PostOfficeEmail.objects.filter(
                snooper__batch_id__batch_type__in=permitted_batch_types,
                snooper__batch_id__organisation=club,
                to=[email_address],
            ).order_by("-pk")[:slice]

            # JPG Query - should this really be testing for the role in EmailBatchRBAC?
            # I think it gives the same result and is more efficient this way, but
            # is perhaps building in a hidden dependency between RBAC roels and batch types
            # The RBAC role is checked if the user tries to access the email.

        else:

            # No releavnt access so return nothing
            post_office_emails = None

    return post_office_emails
