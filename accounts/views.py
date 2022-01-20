# -*- coding: utf-8 -*-
"""Handles all activities associated with user accounts.

This module handles all of the functions relating to users such as creating
accounts, resetting passwords, searches. profiles etc.

"""
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import SuspiciousOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.http import JsonResponse
from django.contrib.auth.views import PasswordResetView
from django.views.decorators.http import require_POST
from fcm_django.models import FCMDevice

from notifications.notifications_views.user import notifications_in_english
from notifications.notifications_views.core import send_cobalt_email_with_template
from logs.views import get_client_ip, log_event
from organisations.models import Organisation
from organisations.views.general import replace_unregistered_user_with_real_user
from rbac.core import rbac_user_has_role
from .models import User, TeamMate, UnregisteredUser, APIToken, UserAdditionalInfo
from .tokens import account_activation_token
from .forms import (
    UserRegisterForm,
    UserUpdateForm,
    PhotoUpdateForm,
    BlurbUpdateForm,
    UserSettingsForm,
)
from forums.models import Post, Comment1, Comment2
from support.models import Incident
from utils.utils import cobalt_paginator
from cobalt.settings import (
    GLOBAL_ORG,
    RBAC_EVERYONE,
    TBA_PLAYER,
    COBALT_HOSTNAME,
    ABF_USER,
    GLOBAL_TITLE,
)
from masterpoints.views import user_summary


def html_email_reset(request):
    """This is necessary so that we can provide an HTML email template
    for the password reset"""

    return PasswordResetView.as_view(
        html_email_template_name="registration/html_password_reset_email.html"
    )(request)


def _check_duplicate_email(user):
    """Check for a duplicate email address for this one"""

    others_same_email = (
        User.objects.filter(email=user.email).exclude(id=user.id).order_by("id")
    )

    for other_same_email in others_same_email:

        html = render_to_string("accounts/duplicate_email.html", {"user": user})

        context = {
            "name": other_same_email.first_name,
            "title": "Someone is Using Your Email Address",
            "email_body": html,
            "subject": "Email notification",
            "box_colour": "danger",
        }

        send_cobalt_email_with_template(
            to_address=other_same_email.email,
            context=context,
            template="system - no button",
        )

    return others_same_email.exists()


def _check_unregistered_user_match(user):
    """See if there is already a user with this system_id in UnregisteredUser and cut across data"""

    unregistered_user = UnregisteredUser.objects.filter(
        system_number=user.system_number
    ).first()

    if not unregistered_user:
        return

    # Call the callbacks

    # Organisations
    replace_unregistered_user_with_real_user(user)

    # Now delete the unregistered user, we don't need it any more
    unregistered_user.delete()


def register(request):
    """User registration form

    This form allows a user to register for the system. The form includes
    Ajax code to look up the system number and pre-fill the first and last name.

    This form also sends the email to the user to confirm the email address
    is valid.

    Args:
        request - standard request object

    Returns:
        HttpResponse
    """

    form = UserRegisterForm(request.POST or None)

    if request.method == "POST":
        # See if this user registered before and didn't activate
        user = (
            User.objects.filter(system_number=request.POST.get("username"))
            .filter(is_active=False)
            .first()
        )
        if user:
            # reload form with this user as base
            form = UserRegisterForm(request.POST, instance=user)

        if form.is_valid():
            return _register_handle_valid_form(form, request)

    return render(request, "accounts/register.html", {"user_form": form})


def _register_handle_valid_form(form, request):
    user = form.save(commit=False)
    user.is_active = False  # not active until email confirmed
    user.system_number = user.username
    user.save()

    _check_duplicate_email(user)

    to_email = form.cleaned_data.get("email")
    html = (
        f"Thank you for signing up to the {GLOBAL_TITLE} site. "
        f"Please click on the link below to activate your account."
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    link = reverse("accounts:activate", kwargs={"uidb64": uid, "token": token})

    context = {
        "name": user.first_name,
        "title": f"Welcome to {GLOBAL_TITLE}",
        "email_body": html,
        "link": link,
        "link_text": "Activate Account",
        "subject": "Activate your Account",
    }

    send_cobalt_email_with_template(
        to_address=to_email, context=context, priority="now"
    )

    # Check if we have a matching UnregisteredUser object and copy data across
    _check_unregistered_user_match(user)

    return render(
        request, "accounts/register_complete.html", {"email_address": to_email}
    )


def activate(request, uidb64, token):
    """User activation form

    This is the link sent to the user over email. If the link is valid, then
    the user is logged in, otherwise they are notified that the link is not
    valid.

    Args:
        request - standard request object
        uidb64 - encrypted user id
        token - generated token

    Returns:
        HttpResponse
    """
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # Check for multiple email addresses
        others_same_email = (
            User.objects.filter(email=user.email).exclude(id=user.id).order_by("id")
        )
        return render(
            request,
            "accounts/activate_complete.html",
            {"user": user, "others_same_email": others_same_email},
        )
    else:
        return HttpResponse("Activation link is invalid or already used!")


def password_reset_request(request):
    """handle password resets from users not logged in"""
    if request.method != "POST":
        password_reset_form = PasswordResetForm()
        return render(
            request,
            "registration/password_reset_form.html",
            {"password_reset_form": password_reset_form},
        )

    password_reset_form = PasswordResetForm(request.POST)

    if not password_reset_form.is_valid():
        return render(
            request,
            "registration/password_reset_form.html",
            {"password_reset_form": password_reset_form},
        )

    email = password_reset_form.cleaned_data["email"]
    associated_users = User.objects.filter(email=email)

    email_body_base = (
        f"You are receiving this email because you requested a password reset for your account with "
        f"{GLOBAL_TITLE}. Click on the link below to reset your password.<br><br>"
    )

    if associated_users.count() > 1:
        email_body_base += (
            "<b>This email address is shared.</b> You should check the name above and "
            "only click on the link sent to the person who wants to reset their password.<br><br>"
        )

    for user in associated_users:

        if user.is_active:
            link_type = "password_reset_confirm"
            link_text = "Reset Password"
            token = default_token_generator.make_token(user)
            email_body = email_body_base
        else:
            link_type = "accounts:activate"
            link_text = "Activate Account"
            token = account_activation_token.make_token(user)
            email_body = (
                email_body_base
                + "<h3>This account has not been activated. You must activate "
                "the account first.</h3><br><br>"
            )

        link = reverse(
            link_type,
            kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": token,
            },
        )

        context = {
            "name": user.first_name,
            "subject": "Password Reset",
            "title": "Password Reset Requested",
            "email_body": email_body,
            "link": link,
            "link_text": link_text,
        }

        send_cobalt_email_with_template(
            to_address=user.email, context=context, priority="now"
        )

    return redirect("password_reset_done")


def loggedout(request):
    """Should review if this is really needed."""
    return render(request, "accounts/loggedout.html")


@login_required()
def change_password(request):
    """Password change form

    Allows a user to change their password.

    Args:
        request - standard request object

    Returns:
        HttpResponse
    """
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(
                request,
                "Your password was successfully updated!",
                extra_tags="cobalt-message-success",
            )
            log_event(
                request=request,
                user=request.user.full_name,
                severity="INFO",
                source="Accounts",
                sub_source="change_password",
                message="Password change successful",
            )
            return redirect("accounts:user_profile")
        else:
            log_event(
                request=request,
                user=request.user.full_name,
                severity="WARN",
                source="Accounts",
                sub_source="change_password",
                message="Password change failed",
            )
            messages.error(
                request,
                "Please correct the error below.",
                extra_tags="cobalt-message-error",
            )
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


@login_required()
def member_detail_m2m_ajax(request):
    """Returns basic public info on a member. ONLY USED BY MEMBER TRANSFER. REPLACE.

    Ajax call to get basic info on a member. Will return an empty json array
    if the member number is invalid.

    Args:
        member_id - member number

    Returns:
        Json array: member, clubs,  global org name.
    """

    if request.method == "GET" and "member_id" in request.GET:
        member_id = request.GET.get("member_id")
        member = get_object_or_404(User, pk=member_id)
        if request.is_ajax:
            global_org = settings.GLOBAL_ORG
            html = render_to_string(
                template_name="accounts/member_ajax.html",
                context={
                    "member": member,
                    "global_org": global_org,
                },
            )
            data_dict = {"data": html}
            return JsonResponse(data=data_dict, safe=False)
    return JsonResponse(data={"error": "Invalid request"})


@login_required()
def member_details_ajax(request):
    """Returns basic public info on a member for the generic member search.

    Ajax call to get basic info on a member. Will return an empty json array
    if the member number is invalid.

    Args:
        member_id - member number
        search_id - used if page has multiple user searches. We just pass this
        through. Optional.

    Returns:
        Json array: member, clubs,  global org name.
    """

    if request.method == "GET":

        if "search_id" in request.GET:
            search_id = request.GET.get("search_id")
        else:
            search_id = None

        if "member_id" in request.GET:
            member_id = request.GET.get("member_id")
            member = get_object_or_404(User, pk=member_id)
            if request.is_ajax:
                global_org = settings.GLOBAL_ORG
                html = render_to_string(
                    template_name="accounts/member_details_ajax.html",
                    context={
                        "member": member,
                        "global_org": global_org,
                        "search_id": search_id,
                    },
                )
                data_dict = {
                    "data": html,
                    "member": "%s" % member,
                    "pic": f"{member.pic}",
                }
                return JsonResponse(data=data_dict, safe=False)
    return JsonResponse(data={"error": "Invalid request"})


@login_required()
def search_ajax(request):
    """Ajax member search function. ONLY USED BY MEMBER TRANSFER. REPLACE.

    Used to search for members by the Member to Member transfer part of Payments.
    Currently very specific to payments. Could be made more generic if other
    parts of the system need a search function.

    Args:
        lastname - partial lastname to search for. Wild cards the ending.
        firstname - partial firstname to search for. Wild cards the ending.

    Returns:
        HttpResponse - either a message or a list of users in HTML format.
    """

    msg = ""

    if request.method == "GET":

        if "lastname" in request.GET:
            search_last_name = request.GET.get("lastname")
        else:
            search_last_name = None

        if "firstname" in request.GET:
            search_first_name = request.GET.get("firstname")
        else:
            search_first_name = None

        if search_first_name and search_last_name:
            members = User.objects.filter(
                first_name__istartswith=search_first_name,
                last_name__istartswith=search_last_name,
            ).exclude(pk=request.user.id)
        elif search_last_name:
            members = User.objects.filter(
                last_name__istartswith=search_last_name
            ).exclude(pk=request.user.id)
        else:
            members = User.objects.filter(
                first_name__istartswith=search_first_name
            ).exclude(pk=request.user.id)

        if request.is_ajax:
            if members.count() > 30:
                msg = "Too many results (%s)" % members.count()
                members = None
            elif members.count() == 0:
                msg = f"No matches found. Have they registered for {GLOBAL_TITLE}? Registration is free."
            html = render_to_string(
                template_name="accounts/search_results.html",
                context={"members": members, "msg": msg},
            )

            data_dict = {"data": html}

            return JsonResponse(data=data_dict, safe=False)

    return render(
        request,
        "accounts/search_results.html",
        context={"members": members, "msg": msg},
    )


@login_required()
def member_search_ajax(request):
    """Ajax member search function. Used by the generic member search.

    Used to search for members by the Member to Member transfer part of Payments.
    Currently very specific to payments. Could be made more generic if other
    parts of the system need a search function.

    Args:
        lastname - partial lastname to search for. Wild cards the ending.
        firstname - partial firstname to search for. Wild cards the ending.
        search_id - used if page has multiple user searches. We just pass this
        through. Optional.

    Returns:
        HttpResponse - either a message or a list of users in HTML format.
    """

    msg = ""

    if request.method == "GET":

        if "search_id" in request.GET:
            search_id = request.GET.get("search_id")
        else:
            search_id = None

        if "lastname" in request.GET:
            search_last_name = request.GET.get("lastname")
        else:
            search_last_name = None

        if "firstname" in request.GET:
            search_first_name = request.GET.get("firstname")
        else:
            search_first_name = None

        # flag to include the user in the output
        if "include_me" in request.GET:
            exclude_list = [RBAC_EVERYONE, TBA_PLAYER]
        else:
            exclude_list = [request.user.id, RBAC_EVERYONE, TBA_PLAYER]

        if search_first_name and search_last_name:
            members = User.objects.filter(
                first_name__istartswith=search_first_name,
                last_name__istartswith=search_last_name,
            ).exclude(pk__in=exclude_list)
        elif search_last_name:
            members = User.objects.filter(
                last_name__istartswith=search_last_name
            ).exclude(pk__in=exclude_list)
        else:
            members = User.objects.filter(
                first_name__istartswith=search_first_name
            ).exclude(pk__in=exclude_list)

        if request.is_ajax:
            if members.count() > 30:
                msg = "Too many results (%s)" % members.count()
                members = None
            elif members.count() == 0:
                msg = f"No matches found. Have they registered for {GLOBAL_TITLE}? Registration is free."
            html = render_to_string(
                template_name="accounts/search_results_ajax.html",
                context={"members": members, "msg": msg, "search_id": search_id},
            )

            data_dict = {"data": html}

            return JsonResponse(data=data_dict, safe=False)

    return render(
        request,
        "accounts/search_results_ajax.html",
        context={"members": members, "msg": msg},
    )


@login_required()
def system_number_search_ajax(request):
    """Ajax system_number search function. Used by the generic member search.

    Args:
        system_number - exact number to search for

    Returns:
        HttpResponse - either a message or a list of users in HTML format.
    """

    if request.method != "GET":
        return JsonResponse(data={"error": "Invalid request"})

    exclude_list = [request.user.system_number, RBAC_EVERYONE, TBA_PLAYER]

    if "system_number" in request.GET:
        system_number = request.GET.get("system_number")
        member = User.objects.filter(system_number=system_number).first()
    else:
        system_number = None
        member = None

    if member and member.system_number not in exclude_list:
        status = "Success"
        msg = "Found member"
        member_id = member.id
    else:
        status = "Not Found"
        msg = f"No matches found for that {GLOBAL_ORG} number. Check they have registered for <strong>{GLOBAL_TITLE}</strong>. Registration is free."
        member_id = 0

    data = {"member_id": member_id, "status": status, "msg": msg}

    data_dict = {"data": data}
    return JsonResponse(data=data_dict, safe=False)


@login_required
def profile(request):
    """Profile update form.

    Allows a user to change their profile settings.

    Args:
        request - standard request object

    Returns:
        HttpResponse
    """

    form = UserUpdateForm(data=request.POST or None, instance=request.user)

    if request.method == "POST" and form.is_valid():

        form.save()
        if "email" in form.changed_data:
            if _check_duplicate_email(request.user):
                messages.warning(
                    request,
                    "This email is also being used by another member. This is allowed, but please check the "
                    "name on the email to see who it was intended for.",
                    extra_tags="cobalt-message-warning",
                )

            # Clear the bounce flag if set
            user_additional_info = UserAdditionalInfo.objects.filter(
                user=request.user
            ).first()
            if user_additional_info and user_additional_info.email_hard_bounce:
                user_additional_info.email_hard_bounce = False
                user_additional_info.email_hard_bounce_reason = None
                user_additional_info.save()

        messages.success(
            request, "Profile Updated", extra_tags="cobalt-message-success"
        )

        # Reload form or dates don't work
        form = UserUpdateForm(instance=request.user)

    blurbform = BlurbUpdateForm(instance=request.user)
    photoform = PhotoUpdateForm(instance=request.user)

    team_mates = TeamMate.objects.filter(user=request.user).order_by(
        "team_mate__first_name"
    )

    user_additional_info = UserAdditionalInfo.objects.filter(user=request.user).first()
    print(user_additional_info)

    # Show tour for this page?
    tour = request.GET.get("tour", None)

    return render(
        request,
        "accounts/profile/profile.html",
        {
            "form": form,
            "blurbform": blurbform,
            "photoform": photoform,
            "team_mates": team_mates,
            "user_additional_info": user_additional_info,
            "tour": tour,
        },
    )


def blurb_form_upload(request):
    """Profile update sub-form. Handles the picture and about fields.

    Allows a user to change their profile settings.

    Args:
        request - standard request object

    Returns:
        HttpResponse
    """

    if request.method == "POST":
        blurbform = BlurbUpdateForm(request.POST, request.FILES, instance=request.user)
        if blurbform.is_valid():
            blurbform.save()
            messages.success(
                request, "Profile Updated", extra_tags="cobalt-message-success"
            )
        else:
            print(blurbform.errors)

    return redirect("accounts:user_profile")


def picture_form_upload(request):
    """Profile update sub-form. Handles the picture

    Allows a user to change their profile settings.

    Args:
        request - standard request object

    Returns:
        HttpResponse
    """

    if request.method == "POST":
        photoform = PhotoUpdateForm(request.POST, request.FILES, instance=request.user)
        if photoform.is_valid():
            photoform.save()
            messages.success(
                request, "Profile Updated", extra_tags="cobalt-message-success"
            )
        else:
            print(photoform.errors)

    return redirect("accounts:user_profile")


@login_required
def public_profile(request, pk):
    """Public Profile form.

    Shows public information about a member.

    Args:
        request - standard request object
        pk - key of User

    Returns:
        HttpResponse
    """

    pub_profile = get_object_or_404(User, pk=pk)

    post_list = Post.objects.filter(author=pub_profile).order_by("-created_date")
    comment1_list = Comment1.objects.filter(author=pub_profile).order_by(
        "-created_date"
    )
    comment2_list = Comment2.objects.filter(author=pub_profile).order_by(
        "-created_date"
    )

    # Get tab id from URL - this means we are on this tab
    tab = request.GET["tab"] if "tab" in request.GET else None
    posts_active = None
    comment1s_active = None
    comment2s_active = None

    # if we are on a tab then get the right page for that tab and page 1 for the others

    if not tab or tab == "posts":
        posts_active = "active"
        posts = cobalt_paginator(request, post_list)
        comment1s = cobalt_paginator(request, comment1_list, page_no=1)
        comment2s = cobalt_paginator(request, comment2_list, page_no=1)
    elif tab == "comment1s":
        comment1s_active = "active"
        posts = cobalt_paginator(request, post_list, page_no=1)
        comment1s = cobalt_paginator(request, comment1_list)
        comment2s = cobalt_paginator(request, comment2_list, page_no=1)
    elif tab == "comment2s":
        comment2s_active = "active"
        posts = cobalt_paginator(request, post_list, page_no=1)
        comment1s = cobalt_paginator(request, comment1_list, page_no=1)
        comment2s = cobalt_paginator(request, comment2_list)

    summary = user_summary(pub_profile.system_number)

    # Admins get more
    payments_admin = bool(rbac_user_has_role(request.user, "payments.global.edit"))
    events_admin = bool(rbac_user_has_role(request.user, "events.global.view"))
    if rbac_user_has_role(request.user, "support.helpdesk.edit"):
        tickets = Incident.objects.filter(reported_by_user=pub_profile.id)
    else:
        tickets = False

    email_admin = bool(rbac_user_has_role(request.user, "notifications.admin.view"))

    user_additional_info = UserAdditionalInfo.objects.filter(user=pub_profile).first()

    return render(
        request,
        "accounts/profile/public_profile.html",
        {
            "profile": pub_profile,
            "posts": posts,
            "comment1s": comment1s,
            "comment2s": comment2s,
            "posts_active": posts_active,
            "comment1s_active": comment1s_active,
            "comment2s_active": comment2s_active,
            "summary": summary,
            "payments_admin": payments_admin,
            "events_admin": events_admin,
            "email_admin": email_admin,
            "tickets": tickets,
            "user_additional_info": user_additional_info,
        },
    )


@login_required
def user_settings(request):
    """User settings form.

    Allow user to choose preferences

    Args:
        request - standard request object

    Returns:
        HttpResponse
    """

    if request.method == "POST":
        form = UserSettingsForm(data=request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Settings saved.", extra_tags="cobalt-message-success"
            )
    else:
        form = UserSettingsForm(instance=request.user)

    notifications_list = notifications_in_english(request.user)

    # Check if user is a developer. When we have more than one role we may need a better approach such as a specific
    # RBAC role for developers.
    is_developer = rbac_user_has_role(request.user, "notifications.realtime_send.edit")

    # If user has a registered FCM device, show them the option to send a test message

    fcm_devices = FCMDevice.objects.filter(user=request.user).order_by("-date_created")

    return render(
        request,
        "accounts/user_settings.html",
        {
            "form": form,
            "notifications_list": notifications_list,
            "is_developer": is_developer,
            "fcm_devices": fcm_devices,
        },
    )


@login_required()
def add_team_mate_ajax(request):
    """Ajax call to add a team mate

    Args:
        request(HTTPRequest): standard request

    Returns:
        HTTPResponse: success, failure or error
    """

    if request.method == "GET":
        member_id = request.GET.get("member_id")
        member = get_object_or_404(User, pk=member_id)
        team_mate = TeamMate.objects.filter(user=request.user, team_mate=member)
        if team_mate:  # already exists
            msg = f"{member.first_name} is already a team mate"
        else:
            team_mate = TeamMate(user=request.user, team_mate=member)
            team_mate.save()
            msg = "Success"

    else:
        msg = "Invalid request"

    response_data = {"message": msg}
    return JsonResponse({"data": response_data})


@login_required()
def delete_team_mate_ajax(request):
    """Ajax call to delete a team mate

    Args:
        request(HTTPRequest): standard request

    Returns:
        HTTPResponse: success, failure or error
    """
    if request.method == "GET":
        member_id = request.GET.get("member_id")
        member = get_object_or_404(User, pk=member_id)
        team_mate = TeamMate.objects.filter(team_mate=member, user=request.user)
        team_mate.delete()
        msg = "Success"

    else:
        msg = "Invalid request"

    response_data = {"message": msg}
    return JsonResponse({"data": response_data})


@login_required()
def toggle_team_mate_ajax(request):
    """Ajax call to switch the state of a team mate

    Args:
        request(HTTPRequest): standard request

    Returns:
        JsonResponse: message and first name
    """

    if request.method == "GET":
        member_id = request.GET["member_id"]
        member = User.objects.get(pk=member_id)
        team_mate = (
            TeamMate.objects.filter(user=request.user).filter(team_mate=member).first()
        )
        team_mate.make_payments = not team_mate.make_payments
        team_mate.save()
        msg = team_mate.make_payments

    else:
        msg = "Invalid request"

    response_data = {"message": msg, "first_name": team_mate.team_mate.first_name}
    return JsonResponse({"data": response_data})


@login_required()
def user_signed_up_list(request):
    """Show users who have signed up

    Args:
        request(HTTPRequest): standard request

    Returns:
        Page
    """

    users = User.objects.order_by("-date_joined")

    things = cobalt_paginator(request, users)

    total_users = User.objects.count()

    return render(
        request,
        "accounts/user_signed_up_list.html",
        {"things": things, "total_users": total_users},
    )


@login_required()
def delete_photo(request):
    """Removes a user picture and resets to default

    Args:
        request(HTTPRequest): standard request

    Returns:
        Page
    """

    request.user.pic = "pic_folder/default-avatar.png"
    request.user.save()
    messages.success(
        request,
        "Your photo has been reset",
        extra_tags="cobalt-message-success",
    )

    return redirect("accounts:user_profile")


def _get_exclude_list_for_search(request):
    """get the exclude list. System IDs and this user are excluded unless include_me is set"""

    # Check for include_me flag, otherwise don't include current user
    include_me = bool(request.POST.get("include_me"))

    # ignore system accounts
    exclude_list = [RBAC_EVERYONE, TBA_PLAYER, ABF_USER]

    # Ignore this user unless overridden
    if not include_me:
        exclude_list.append(request.user.id)

    return include_me, exclude_list


@login_required()
@require_POST
def member_search_htmx(request):
    """Search on user first and last name.

    The goal of the member search is to finally replace the included search with a hidden user_id input field,
    the users name and a button to search again. Alternatively, a callback can be provided which will be called
    if/when a user is selected.

    All parameters are passed through in the request:

    search_id:     optional identifier, required if there are multiple user searches on same page, must be unique
                   but can be anything. Gets appended to any DOM objects that should be unique on the page. This is
                   also used as the prefix for the final user_id field if user_id_field is not specified.
    user_id_field: Optional. At the end, if we find a matching user we will create an element for the user_id and
                   an element for the user name to display. The user_id_field will be used as the name of the
                   user_id input. If not specified then member{search_id} is used.
    include_me:    Flag to include the logged in user in the search. Default is no.
    callback:      Optional. If provided then this will be called when a member is picked.
    """

    # Get parameters
    search_id = request.POST.get("search_id", "")
    user_id_field = request.POST.get("user_id_field", "")
    callback = request.POST.get("callback", "")

    # Get partial first name to search for from form
    last_name_search = request.POST.get("last_name_search")
    first_name_search = request.POST.get("first_name_search")

    # If user enters data and then deletes it we can get nothing through - ignore
    if not last_name_search and not first_name_search:
        return HttpResponse("")

    # ignore system accounts
    include_me, exclude_list = _get_exclude_list_for_search(request)

    if last_name_search and first_name_search:
        name_list = (
            User.objects.filter(last_name__istartswith=last_name_search)
            .filter(first_name__istartswith=first_name_search)
            .exclude(pk__in=exclude_list)
        )
    elif last_name_search:
        name_list = User.objects.filter(
            last_name__istartswith=last_name_search
        ).exclude(pk__in=exclude_list)
    else:
        name_list = User.objects.filter(
            first_name__istartswith=first_name_search
        ).exclude(pk__in=exclude_list)

    # See if there is more data
    more_data = False
    if name_list.count() > 10:
        more_data = True
        name_list = name_list[:10]

    return render(
        request,
        "accounts/search/member_search_htmx.html",
        {
            "name_list": name_list,
            "more_data": more_data,
            "search_id": search_id,
            "user_id_field": user_id_field,
            "include_me": include_me,
            "callback": callback,
        },
    )


@login_required()
@require_POST
def system_number_search_htmx(request):
    """Search on system number"""

    # Get parameters
    search_id = request.POST.get("search_id", "")
    user_id_field = request.POST.get("user_id_field", "")
    callback = request.POST.get("callback", "")
    # Get partial first name to search for from form
    system_number = request.POST.get("system_number_search")

    if system_number == "":
        return HttpResponse(
            "<span class='cobalt-form-error''>Enter a number to look up, or type in the name fields</span>"
        )

    # ignore system accounts
    include_me, exclude_list = _get_exclude_list_for_search(request)

    member = (
        User.objects.filter(system_number=system_number)
        .exclude(pk__in=exclude_list)
        .first()
    )

    if member:
        return render(
            request,
            "accounts/search/name_match_htmx.html",
            {
                "member": member,
                "search_id": search_id,
                "user_id_field": user_id_field,
                "include_me": include_me,
                "callback": callback,
            },
        )
    else:
        return HttpResponse("No match found")


@login_required()
@require_POST
def member_match_htmx(request):
    """show member details when a user picks from the list of matches"""

    # Get parameters
    member_id = request.POST.get("member_id")
    search_id = request.POST.get("search_id", "")
    user_id_field = request.POST.get("user_id_field", "")
    callback = request.POST.get("callback", "")

    # ignore system accounts
    include_me, exclude_list = _get_exclude_list_for_search(request)

    member = User.objects.filter(pk=member_id).exclude(pk__in=exclude_list).first()

    if member:
        return render(
            request,
            "accounts/search/name_match_htmx.html",
            {
                "member": member,
                "search_id": search_id,
                "user_id_field": user_id_field,
                "include_me": include_me,
                "callback": callback,
            },
        )
    else:
        return HttpResponse("No match found")


@login_required()
@require_POST
def member_match_summary_htmx(request):
    """show outcome from search"""

    # Get parameters
    member_id = request.POST.get("member_id")
    search_id = request.POST.get("search_id", "")
    user_id_field = request.POST.get("user_id_field", "")
    include_me = bool(request.POST.get("include_me"))

    member = get_object_or_404(User, pk=member_id)

    return render(
        request,
        "accounts/search/name_match_summary_htmx.html",
        {
            "member": member,
            "search_id": search_id,
            "user_id_field": user_id_field,
            "include_me": include_me,
        },
    )


def check_system_number(system_number):
    """Check if system number is valid and also if it is registered already in Cobalt, either as a member or as an
    unregistered user

    Args:
        system_number (int): number to check

    Returns:
        list: is_valid (bool), is_in_use_member (bool), is_in_use_un_reg (bool)

    Returns whether this is a valid (current, active) ABF number, whether we have a user registered with this
    number already or not, whether we have an unregistered user already with this number
    """

    # TODO: Add visitors

    summary = user_summary(system_number)
    is_valid = bool(summary)
    is_in_use_member = User.objects.filter(system_number=system_number).exists()
    is_in_use_un_reg = UnregisteredUser.objects.filter(
        system_number=system_number
    ).exists()

    return is_valid, is_in_use_member, is_in_use_un_reg


def invite_to_join(
    un_reg: UnregisteredUser,
    email: str,
    requested_by_user: User,
    requested_by_org: Organisation,
):
    """Invite an unregistered user to sign up"

    Args:
        un_reg: An unregistered user object
        email: email address to send to
        requested_by_user: User who is inviting this person
        requested_by_org: Org making request

    """

    email_body = f"""
                    {requested_by_user.full_name} from {requested_by_org} is inviting you to sign up for
                    {GLOBAL_TITLE}. This is free for {GLOBAL_ORG} members.
                    <br><br>
                    Benefits of signing up include:
                    <ul>
                    <li>View and enter events across the country
                    <li>Use a single account to pay for all you bridge at participating clubs
                    <li>Use credit card auto top up to add funds to your account automatically
                    <li>Use club pre-paid systems to pay for your normal duplicate bridge
                    <li>Manage your preference to receive information on things that interest you
                    <li>Use forums to follow topics of interest and to communicate with other members
                    </ul>
                    Click the link below to sign up now. It's Free!
                    <br><br>
    """
    link = reverse("accounts:register")

    context = {
        "name": un_reg.first_name,
        "title": f"Sign Up for {GLOBAL_TITLE}",
        "link_text": "Sign Up",
        "link": link,
        "email_body": email_body,
    }

    send_cobalt_email_with_template(to_address=email, context=context)

    un_reg.last_registration_invite_sent = timezone.now()
    un_reg.last_registration_invite_by_user = requested_by_user
    un_reg.last_registration_invite_by_club = requested_by_org
    un_reg.save()


@login_required()
def covid_htmx(request):
    """return current state of users covid status as HTML"""

    return render(request, "accounts/profile/covid_htmx.html")


@login_required()
def covid_user_confirm_htmx(request):
    """Update users covid status"""

    request.user.covid_status = request.user.CovidStatus.USER_CONFIRMED
    request.user.save()
    return render(request, "accounts/profile/covid_htmx.html")


@login_required()
def covid_user_exempt_htmx(request):
    """Update users covid status to anti-vaxxer"""

    request.user.covid_status = request.user.CovidStatus.USER_EXEMPT
    request.user.save()
    return render(request, "accounts/profile/covid_htmx.html")


@login_required()
def developer_settings_htmx(request):
    """Manage settings for developers. Built into the normal settings page"""

    if "add" in request.POST:
        APIToken(user=request.user).save()

    api_tokens = APIToken.objects.filter(user=request.user)

    return render(
        request, "accounts/developer/settings.html", {"api_tokens": api_tokens}
    )


@login_required()
def developer_settings_delete_token_htmx(request):
    """Delete a token for a developer"""

    APIToken.objects.filter(pk=request.POST.get("token_id"), user=request.user).delete()

    api_tokens = APIToken.objects.filter(user=request.user)

    return render(
        request, "accounts/developer/settings.html", {"api_tokens": api_tokens}
    )


@login_required()
@require_POST
def admin_toggle_user_is_active(request):
    """Activate or deactivate a user"""

    if not request.user.is_superuser:
        return HttpResponse("Forbidden")

    if "user_id" in request.POST:

        user_id = request.POST.get("user_id")
        user = get_object_or_404(User, pk=user_id)
        user.is_active = not user.is_active
        user.save()

        log_event(
            request.user,
            "WARN",
            "Accounts",
            "admin-activate",
            f"{user} is_active status changed to {user.is_active}",
        )

    return render(
        request, "accounts/profile/public_profile_header_admin.html", {"profile": user}
    )
