from django.urls import reverse
from django.utils.html import format_html

from accounts.models import User, UnregisteredUser


def link_to_user_or_unregistered_user(system_number: int):
    """ Add a link to the user/unregistered user from Django admin views that have system number only  """

    user_type = "Unknown"
    url = ""
    user = User.objects.filter(system_number=system_number).first()
    if user:
        user_type = "User"
        url = reverse("accounts:public_profile", kwargs={"pk": user.id})
    else:
        user = UnregisteredUser.objects.filter(system_number=system_number).first()
        if user:
            user_type = "Unregistered"
            url = reverse("accounts:unregistered_public_profile", kwargs={"pk": user.id})

    return format_html(f"<a href='{url}'>{user_type} - {user}</a>")
