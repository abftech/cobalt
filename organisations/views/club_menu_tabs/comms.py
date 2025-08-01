import logging
import mimetypes
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from accounts.models import User, UnregisteredUser
from accounts.views.core import get_users_or_unregistered_users_from_email_list
from cobalt.settings import COBALT_HOSTNAME
from notifications.forms import OrgEmailForm
from notifications.models import Snooper, EmailBatchRBAC, EmailAttachment, BatchID
from notifications.views.core import (
    send_cobalt_email_with_template,
    create_rbac_batch_id,
)
from organisations.decorators import check_club_menu_access
from organisations.forms import TagMultiForm, FrontPageForm, EmailAttachmentForm
from organisations.models import (
    ClubTag,
    MemberClubTag,
    MemberMembershipType,
    OrganisationFrontPage,
    OrgEmailTemplate,
    ClubLog,
)
from organisations.views.club_menu_tabs.settings import tags_htmx
from organisations.views.club_menu_tabs.utils import (
    get_club_members_from_system_number_list,
    get_members_for_club,
)

from rbac.core import rbac_user_has_role
from rbac.views import rbac_forbidden
from utils.utils import cobalt_paginator

logger = logging.getLogger("cobalt")


# Comms check removed as access required by someone with congress only access
# @check_club_menu_access(check_comms=True)
@check_club_menu_access()
def email_htmx(request, club, message=None):
    """build the comms email tab in club menu"""

    # check relevant user access

    if rbac_user_has_role(request.user, "notifications.admin.view"):
        # Global comms access
        comms_access = True
        congress_view_access = True

        # may also have club specific or global event access
        congress_edit_access = rbac_user_has_role(
            request.user, f"events.org.{club.id}.edit"
        )

    else:
        # Club specific comms access
        comms_access = rbac_user_has_role(
            request.user, f"notifications.orgcomms.{club.id}.edit"
        )

        # club or gloabl event update access
        congress_edit_access = rbac_user_has_role(
            request.user, f"events.org.{club.id}.edit"
        )
        if congress_edit_access:
            congress_view_access = True
        else:
            congress_view_access = rbac_user_has_role(
                request.user, f"events.org.{club.id}.view"
            )

    if not (comms_access or congress_view_access or congress_edit_access):
        # No releavnt access so block and tell them about the comms role
        return rbac_forbidden(request, f"notifications.org.{club.id}.edit", htmx=True)

    # build a list of permitted batch types to view for this user
    # and a list of the WIP batch types they can edit or delete
    if comms_access:
        permitted_batch_types = [
            BatchID.BATCH_TYPE_ADMIN,
            BatchID.BATCH_TYPE_COMMS,
            BatchID.BATCH_TYPE_RESULTS,
        ]
        editable_batch_types = permitted_batch_types[:]
    else:
        permitted_batch_types = []
        editable_batch_types = []

    if congress_edit_access or congress_view_access:
        permitted_batch_types += [
            BatchID.BATCH_TYPE_CONGRESS,
            BatchID.BATCH_TYPE_EVENT,
            BatchID.BATCH_TYPE_MULTI,
            BatchID.BATCH_TYPE_ENTRY,
        ]
        if congress_edit_access:
            editable_batch_types += [
                BatchID.BATCH_TYPE_CONGRESS,
                BatchID.BATCH_TYPE_EVENT,
                BatchID.BATCH_TYPE_MULTI,
                BatchID.BATCH_TYPE_ENTRY,
            ]

    # build a list of batch types to include in the selector
    batch_types = [
        (option, description)
        for (option, description) in BatchID.BATCH_TYPE
        if option in permitted_batch_types
    ]

    # determine which batch types to show
    if request.method == "POST":
        batch_type_selected = request.POST.get("batch_type_picker")
        if not batch_type_selected:
            batch_type_selected = "ALL"
    else:
        batch_type_selected = "ALL"

    if batch_type_selected == "ALL":
        batch_types_to_show = [batch_type for (batch_type, _) in batch_types]
    else:
        batch_types_to_show = [batch_type_selected]

    # get the batch header information
    batches = BatchID.objects.filter(
        batch_type__in=batch_types_to_show, organisation=club
    ).order_by("-pk")

    things = cobalt_paginator(request, batches)

    return render(
        request,
        "organisations/club_menu/comms/email_htmx.html",
        {
            "club": club,
            "message": message,
            "things": things,
            "batch_types": batch_types,
            "type_selected": batch_type_selected,
            "comms_access": comms_access,
            "congress_edit_access": congress_edit_access,
            "congress_view_access": congress_view_access,
            "editable_batch_types": editable_batch_types,
        },
    )


@check_club_menu_access(check_comms=True)
def edit_inflight_batch_htmx(request):
    """Resume editing an incomplete batch"""

    return HttpResponse("Coming soon - Edit inflight batch")


@check_club_menu_access(check_comms=True)
def delete_inflight_batch_htmx(request):

    return HttpResponse("Coming soon - Delete inflight batch")


# JPG TO DO deprecate?
def _send_email_to_tags(request, club, tags, email_form, club_template, attachments):
    """Send an email to a group of members identified by tags

    Updated for sprint-48 batch header information"""

    # let anyone with comms access to this org view them
    batch_id = create_rbac_batch_id(
        rbac_role=f"notifications.orgcomms.{club.id}.edit",
        user=request.user,
        organisation=club,
        batch_type=BatchID.BATCH_TYPE_COMMS,
        description=email_form.cleaned_data["subject"],
        complete=True,
    )

    # Check for Tag=0, means everyone
    if 0 in tags:
        tag_system_numbers = (
            MemberMembershipType.objects.filter(membership_type__organisation=club)
            .distinct("system_number")
            .values("system_number")
        )
    else:
        tag_system_numbers = (
            MemberClubTag.objects.filter(club_tag__in=tags)
            .distinct("system_number")
            .values("system_number")
        )

    logger.debug(f"tag_system_numbers: {tag_system_numbers}")

    # Get real members
    members = User.objects.filter(system_number__in=tag_system_numbers)

    # Get unregistered
    un_regs = UnregisteredUser.objects.filter(system_number__in=tag_system_numbers)

    # get club level email

    # JPG deprecated reference until entire function deleted
    club_email_addresses = None
    # club_email_addresses = Member@Club@Email.objects.filter(
    #     system_number__in=tag_system_numbers, organisation=club
    # )

    # convert to dict
    club_email_addresses_dict = {
        item.system_number: item.email for item in club_email_addresses
    }

    if not members and not un_regs:
        return "There are no recipients for this email"

    recipient_count = 0

    # Handle members
    for member in members:

        # COB-793 batch size added

        _send_email_sub(
            first_name=member.first_name,
            email=member.email,
            email_form=email_form,
            batch_id=batch_id,
            club_template=club_template,
            attachments=attachments,
            batch_size=len(members) + len(un_regs),
        )

        recipient_count += 1

    # Handle un_registered

    for un_reg in un_regs:
        email = club_email_addresses_dict.get(un_reg.system_number)
        if email:

            # COB-793 batch size added

            _send_email_sub(
                first_name=un_reg.first_name,
                email=email,
                email_form=email_form,
                batch_id=batch_id,
                club_template=club_template,
                attachments=attachments,
                unregistered_identifier=un_reg.identifier,
                batch_size=len(members) + len(un_regs),
            )

            recipient_count += 1

    # update the BatchID with the batch size

    batch = BatchID.objects.get(batch_id=batch_id)
    batch.batch_size = recipient_count
    batch.save()

    return f"Email queued to send to {recipient_count} recipients"


def _send_email_sub(
    first_name,
    email,
    email_form,
    batch_id=None,
    club_template=None,
    attachments=None,
    unregistered_identifier=None,
    batch_size=1,
):
    """Send an email subtask

    Args:
        first_name(str): name of person to send to
        email(str): email address
        email_form: OrgEmailForm which user has just completed
        batch_id(BatchID): batch id if required
        club_template(OrgEmailTemplate): has banner, footer etc for club
        attachments(dict): dict of attachments ('filename', 'path-to-file')
        batch_size(int): number of emails in batch (for COB-793)
    """

    logger.debug(f"email address is {email}")

    context = {
        "name": first_name,
        "subject": email_form.cleaned_data["subject"],
        "title": email_form.cleaned_data["subject"],
        "email_body": email_form.cleaned_data["org_email_body"],
        "unregistered_identifier": unregistered_identifier,
    }

    # Get the extra fields that could have been overridden by the user
    reply_to = email_form.cleaned_data["reply_to"]
    from_name = email_form.cleaned_data["from_name"]

    sender = f"{from_name}<donotreply@myabf.com.au>" if from_name else None

    if not club_template:
        club_template = OrgEmailTemplate()

    context["img_src"] = club_template.banner.url
    context["footer"] = club_template.footer
    context["box_colour"] = club_template.box_colour
    context["box_font_colour"] = club_template.box_font_colour

    # COB-793 : added batch size for notifications management

    send_cobalt_email_with_template(
        to_address=email,
        context=context,
        batch_id=batch_id,
        template="system - club",
        reply_to=reply_to,
        sender=sender,
        attachments=attachments,
        batch_size=batch_size,
    )


@check_club_menu_access(check_comms=True)
def entrant_email_send_htmx(request, club):
    """Send an email to a range of congresses and/or events

    Note: club argument is added by the check_club_menu_access decorator"""

    return HttpResponse("Coming soon - compose an entrant email")


# JPG TO DO Deprecate
@check_club_menu_access(check_comms=True)
def email_send_htmx(request, club):
    """send an email"""

    message = None

    # We either get "test" to send a test message, "send" to send it, or nothing to show the empty form.
    if "test" not in request.POST and "send" not in request.POST:
        email_form = OrgEmailForm(club=club)
        tag_form = TagMultiForm(club=club)
    else:
        email_form = OrgEmailForm(request.POST, club=club)
        tag_form = TagMultiForm(request.POST, club=club)
        if not (email_form.is_valid() and tag_form.is_valid()):
            return HttpResponse(
                f"""<span
                        class='text-danger font-weight-bold'
                        _='on load wait 5 seconds
                        then transition opacity to 0
                        over 2 seconds
                        then remove me'
                        >There is an error in the data. Please look through the tabs and correct it.
                        </span>
                        {email_form.errors}
                        {tag_form.errors}
                        """
            )

        # Load template once if possible
        if email_form.cleaned_data["template"]:
            template_id = email_form.cleaned_data["template"]
            club_template = get_object_or_404(OrgEmailTemplate, pk=template_id)
        else:
            # Create but don't save so we get the club admin logo, not the system default
            club_template = OrgEmailTemplate()

        # Get any attachments and convert to Django post office expected format
        # COB-794 - attachments not accessible on iOS email client. Try adding mimetype
        attachment_ids = request.POST.getlist("selected_attachments")
        attachments = {}
        total_size = 0.0
        if attachment_ids:
            attachments_objects = EmailAttachment.objects.filter(id__in=attachment_ids)
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

        # Check for maximum size of attachments
        if total_size > 10_000_000:
            return HttpResponse(
                """<span
                        class='text-danger font-weight-bold'
                        _='on load wait 5 seconds
                        then transition opacity to 0
                        over 2 seconds
                        then remove me'
                        >Attachments are too large to send. Maximum size is 10Mb. Please remove something or send as links.
                        </span>
                        """
            )

        if "test" in request.POST:
            _send_email_sub(
                first_name=request.user.first_name,
                email=request.user.email,
                email_form=email_form,
                club_template=club_template,
                attachments=attachments,
            )

            return HttpResponse(
                """<span
                                        class='text-primary font-weight-bold'
                                        _='on load wait 5 seconds
                                        then transition opacity to 0
                                        over 2 seconds
                                        then remove me'
                                        >Test email sent. Check your inbox.
                                        </span>"""
            )
        else:

            # convert tags from strings to ints
            send_tags = list(map(int, tag_form.cleaned_data["selected_tags"]))

            message = _send_email_to_tags(
                request=request,
                club=club,
                tags=send_tags,
                email_form=email_form,
                club_template=club_template,
                attachments=attachments,
            )
            return email_htmx(request, message=message)

    # Get tags, we include an everyone tag inside the template
    tags = ClubTag.objects.filter(organisation=club).order_by("tag_name")

    # Get total members for the Everyone option and also to block sending if there are no members
    total_members = (
        MemberMembershipType.objects.filter(membership_type__organisation=club)
        .distinct("system_number")
        .count()
    )

    # Get the number of members with each tag
    tag_count = {"EVERYONE": total_members}
    empty_tags = []

    for tag in tags:
        this_count = (
            MemberClubTag.objects.filter(club_tag=tag).distinct("system_number").count()
        )
        tag_count[tag.tag_name] = this_count
        if this_count == 0:
            empty_tags.append(tag.id)

    # Fill reply_to and from_name with values from the first template if there is one
    first_template = (
        OrgEmailTemplate.objects.filter(organisation=club).order_by("pk").first()
    )
    if first_template:
        email_form.fields["from_name"].initial = first_template.from_name
        email_form.fields["reply_to"].initial = first_template.reply_to

    return render(
        request,
        "organisations/club_menu/comms/email_send_htmx.html",
        {
            "club": club,
            "email_form": email_form,
            "tag_form": tag_form,
            "tags": tags,
            "tag_count": tag_count,
            "message": message,
            "no_members": total_members == 0,
            "empty_tags": empty_tags,
        },
    )


@check_club_menu_access(check_comms=True)
def email_view_htmx(request, club):
    """view an email"""

    batch_id = request.POST.get("batch_id")

    # NOTE : batch_id in this context is the key to
    # the EmailBatchRBAC record, not the BatchID record

    # Get the matching batch
    email_batch = EmailBatchRBAC.objects.prefetch_related(
        "batch_id__snooper_set__post_office_email"
    ).get(pk=batch_id)

    # We allow people with explicit access to see emails or global admins, not state admins
    if not (
        rbac_user_has_role(request.user, email_batch.rbac_role)
        or rbac_user_has_role(request.user, "orgs.admin.edit")
    ):
        return rbac_forbidden(request, email_batch.rbac_role)

    # Get the snoopers for this batch
    snoopers = Snooper.objects.select_related("post_office_email").filter(
        batch_id=email_batch.batch_id
    )

    # Get totals from the database
    db_totals = snoopers.aggregate(
        sent=Count("ses_sent_at"),
        delivered=Count("ses_delivered_at"),
        opened=Count("ses_last_opened_at"),
        clicked=Count("ses_last_clicked_at"),
        bounced=Count("ses_last_bounce_at"),
    )

    # Total count
    count = snoopers.count()

    # Handle empty batch case
    if count == 0:
        return render(
            request,
            "organisations/club_menu/comms/email_view_htmx.html",
            {
                "club": club,
                "email_batch": email_batch,
                "details": {
                    "number_sent": 0,
                    "created": None,
                    "subject": "No emails in batch",
                    "totals": {},
                    "po_counts": {
                        "sent": 0,
                        "failed": 0,
                        "queued": 0,
                        "requeued": 0,
                    },
                },
                "large_batch": False,
            },
        )

    # We only show the first email
    snooper = snoopers.first()

    totals = {}

    # Build dictionary of items from Snoopers - this is how the email got on after we sent it according to AWS SES
    for db_total in db_totals:
        line = {
            "name": db_total.split("_")[-1],
            "amount": db_totals[db_total],
            "percent": int(db_totals[db_total] * 100.0 / count),
        }
        if line["percent"] == 100:
            line["colour"] = "success"
        elif line["percent"] >= 80:
            line["colour"] = "primary"
        elif line["percent"] >= 60:
            line["colour"] = "info"
        elif line["percent"] >= 40:
            line["colour"] = "warning"
        else:
            line["colour"] = "danger"
        # Bounces are always bad
        if line["name"] == "bounced":
            line["colour"] = "danger"
        totals[db_total] = line

    # Now build status of what Django Post Office knows
    po_counts = snoopers.aggregate(
        sent=Count("pk", filter=Q(post_office_email__status=0)),
        failed=Count("pk", filter=Q(post_office_email__status=1)),
        queued=Count("pk", filter=Q(post_office_email__status=2)),
        requeued=Count("pk", filter=Q(post_office_email__status=3)),
    )

    details = {
        "number_sent": count,
        "created": snooper.post_office_email.created,
        "subject": snooper.post_office_email.context["subject"],
        "totals": totals,
        "po_counts": po_counts,
    }

    # COB-793
    return render(
        request,
        "organisations/club_menu/comms/email_view_htmx.html",
        {
            "club": club,
            "email_batch": email_batch,
            "details": details,
            "large_batch": snooper.limited_notifications,
        },
    )


@check_club_menu_access(check_comms=True)
def delete_tag_htmx(request, club):
    """Delete a tag"""

    tag_id = request.POST.get("tag_id")
    tag = get_object_or_404(ClubTag, pk=tag_id)
    if tag.organisation == club:
        tag.delete()

    return tags_htmx(request)


@check_club_menu_access(check_comms=True)
def tags_add_user_tag(request, club):
    """Add a tag to a user"""

    tag_id = request.POST.get("tag_id")
    tag = get_object_or_404(ClubTag, pk=tag_id)
    system_number = request.POST.get("system_number")

    if tag.organisation == club:
        MemberClubTag(club_tag=tag, system_number=system_number).save()
        return HttpResponse("Tag Added")

    return HttpResponse("Error")


@check_club_menu_access(check_comms=True)
def tags_remove_user_tag(request, club):
    """Remove a tag from a user"""

    tag_id = request.POST.get("tag_id")
    tag = get_object_or_404(ClubTag, pk=tag_id)
    system_number = request.POST.get("system_number")

    if tag.organisation == club:
        member_tag = MemberClubTag.objects.filter(
            club_tag=tag, system_number=system_number
        )
        member_tag.delete()
        return HttpResponse("Tag Removed")

    return HttpResponse("Error")


@check_club_menu_access(check_comms=True)
def public_info_htmx(request, club):
    """build the comms public info tab in club menu"""

    front_page, _ = OrganisationFrontPage.objects.get_or_create(organisation=club)

    message = ""

    if "save" in request.POST:
        front_page_form = FrontPageForm(request.POST, instance=front_page)
        if front_page_form.is_valid():
            front_page_form.save()
            message = "Data saved"
            # log it
            ClubLog(
                organisation=club,
                actor=request.user,
                action="Updated public profile",
            ).save()
        else:
            print(front_page_form.errors)

    else:
        front_page_form = FrontPageForm(instance=front_page)

    return render(
        request,
        "organisations/club_menu/comms/public_info_htmx.html",
        {
            "club": club,
            "front_page_form": front_page_form,
            "message": message,
            "front_page": front_page,
        },
    )


@login_required()
def email_preview_htmx(request):
    """Preview an email as user creates it"""

    # We may or may not get a template
    template_id = request.POST.get("template")
    if template_id:
        template = get_object_or_404(OrgEmailTemplate, pk=template_id)
    else:
        template = OrgEmailTemplate()

    # Get user input
    title = request.POST.get("subject")
    email_body = request.POST.get("org_email_body")

    # Apostrophe's blow up the iframe so change to code
    email_body = email_body.replace("'", "&#39;")

    # Get attachments if any
    attachment_ids = request.POST.getlist("selected_attachments")
    if attachment_ids:
        attachments_objects = EmailAttachment.objects.filter(id__in=attachment_ids)
    else:
        attachments_objects = None

    return render(
        request,
        "organisations/club_menu/comms/email_preview_htmx.html",
        {
            "template": template,
            "img_src": template.banner.url,
            "host": COBALT_HOSTNAME,
            "title": title,
            "email_body": email_body,
            "attachment_objects": attachments_objects,
        },
    )


# JPG To Do Deprecated
@check_club_menu_access(check_comms=True)
def from_and_reply_to_htmx(request, club):
    """rebuild the from and reply_to fields in the send email form if the template changes"""

    template_id = request.POST.get("template")
    template = get_object_or_404(OrgEmailTemplate, pk=template_id)

    email_form = OrgEmailForm(club=club)

    email_form.fields["from_name"].initial = template.from_name
    email_form.fields["reply_to"].initial = template.reply_to

    return render(
        request,
        "organisations/club_menu/comms/email_send_from_and_reply_to_htmx.html",
        {"email_form": email_form},
    )


@check_club_menu_access(check_comms=True)
def email_attachment_htmx(request, club):
    """Upload an email attachment"""

    # JPG TO DO: Deprecate - moved to compose_email_content_attachment_htmx

    # TODO: Move this to notifications and make it more generic - organisation or member

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
        "organisations/club_menu/comms/email_attachment_htmx.html",
        {"club": club, "email_attachments": email_attachments},
    )


# JPG TO DO Deprecated - moved to notifications
def _email_attachment_list_htmx(request, club, hx_trigger_response=None):
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
        "organisations/club_menu/comms/email_attachment_list_htmx.html",
        {"club": club, "email_attachments": email_attachments},
    )

    if hx_trigger_response:
        response["HX-Trigger"] = hx_trigger_response

    return response


@check_club_menu_access(check_comms=True)
def upload_new_email_attachment_htmx(request, club):
    """Upload a new email attachment for a club
    Use the HTMX hx-trigger response header to tell the browser about it
    """

    form = EmailAttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        email_attachment = form.save(commit=False)
        email_attachment.organisation = club
        email_attachment.save()

        trigger = f"""{{"post_attachment_add":{{"id": "{email_attachment.id}" , "name": "{email_attachment.filename()}"}}}}"""

        return _email_attachment_list_htmx(request, club, hx_trigger_response=trigger)

    return HttpResponse("Error")


@check_club_menu_access(check_comms=True)
def delete_email_attachment_htmx(request, club):
    """Delete an email attachment for a club.
    This one is a little tricky as we also need to tell the browser to trigger an event to remove this from
    the list of attachments if present.
    For this we use the HTMX hx-trigger response header
    """

    email_attachment_id = request.POST.get("email_attachment_id")
    email_attachment = get_object_or_404(EmailAttachment, pk=email_attachment_id)

    if email_attachment.organisation != club:
        return HttpResponse("Access Denied")

    # Delete file
    email_attachment.attachment.delete(False)
    # Delete database object
    email_attachment.delete()

    trigger = f"""{{"post_attachment_delete": "{email_attachment_id}"}}"""

    return _email_attachment_list_htmx(request, club, hx_trigger_response=trigger)


@check_club_menu_access(check_comms=True)
def club_menu_tab_comms_emails_from_tags_htmx(request, club):
    """takes in tags and lists out who will be emailed. Called from the email wizard"""

    tag_list = request.POST.getlist("selected_tags")

    # Check for everyone
    if "0" in tag_list:
        members = get_members_for_club(club)
    else:
        # not everyone, so load members for these tags
        system_numbers = MemberClubTag.objects.filter(
            club_tag__pk__in=tag_list
        ).values_list("system_number")
        members = get_club_members_from_system_number_list(system_numbers, club)

    return render(
        request,
        "organisations/club_menu/comms/emails_from_tags_htmx.html",
        {"members": members},
    )


# TO DO - move to notifications
@check_club_menu_access(check_comms=True)
def email_recipients_list_htmx(request, club):
    """show the recipients for a batch of emails."""

    batch_id_id = request.POST.get("batch_id_id")

    snoopers = Snooper.objects.select_related("post_office_email").filter(
        batch_id=batch_id_id
    )

    # Get email addresses that received this
    email_list = [snooper.post_office_email.to[0] for snooper in snoopers]

    user_dict = get_users_or_unregistered_users_from_email_list(email_list)

    # augment snoopers
    for snooper in snoopers:
        if snooper.post_office_email.to[0] in user_dict:
            snooper.member = user_dict[snooper.post_office_email.to[0]]

    return render(
        request,
        "organisations/club_menu/comms/email_recipients_list_htmx.html",
        {"batch_id_id": batch_id_id, "snoopers": snoopers},
    )
