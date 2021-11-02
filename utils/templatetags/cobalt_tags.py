import random

from django import template
from django.template.defaultfilters import striptags
from django.template.loader import get_template
from django.utils.dateformat import DateFormat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.humanize.templatetags.humanize import intcomma
from widget_tweaks.templatetags.widget_tweaks import render_field, FieldAttributeNode

from cobalt.settings import GLOBAL_CURRENCY_SYMBOL

register = template.Library()


@register.filter(name="cobalt_time", expects_localtime=True)
def cobalt_time(value):
    """Custom filter for datetime so we can get "am" amd "pm" instead of "a.m." and "p.m."
    Accepted datetime object or time object
    Returns e.g. 10am, 7:15pm 10:01am"""

    if not value:
        return None

    hour_str = value.strftime("%I")
    min_str = value.strftime("%M")
    ampm_str = value.strftime("%p").replace(".", "").lower()
    hour_num = "%d" % int(hour_str)

    if min_str == "00":
        return f"{hour_num}{ampm_str}"
    else:
        return f"{hour_num}:{min_str}{ampm_str}"


@register.filter(name="cobalt_nice_date", expects_localtime=True)
def cobalt_nice_date(value):
    """custom filter for date to format as full date"""
    if not value:
        return None

    return DateFormat(value).format("l jS M Y")


@register.filter(name="cobalt_nice_datetime", expects_localtime=True)
def cobalt_nice_datetime(value):
    """Custom filter for datetime to format as full date"""
    if not value:
        return None

    date_part = cobalt_nice_date(value)
    time_part = cobalt_time(value)

    return f"{date_part} {time_part}"


@register.filter(name="cobalt_user_link", is_safe=True)
def cobalt_user_link(user):
    """Custom filter for user which includes link to public profile. Could possibly be extended to add a hover"""
    if not user:
        return None

    url = reverse("accounts:public_profile", kwargs={"pk": user.id})
    return format_html("<a href='{}'>{}</a>", mark_safe(url), user)


@register.filter(name="cobalt_user_link_short", is_safe=True)
def cobalt_user_link_short(user):
    """Custom filter for user which includes link to public profile.
    Short version - name only, no system number."""
    if not user:
        return None
    try:
        url = reverse("accounts:public_profile", kwargs={"pk": user.id})
        return format_html(
            "<a target='_blank' href='{}'>{}</a>", mark_safe(url), user.full_name
        )
    # Try to return the object if it was not a User
    except AttributeError:
        return user


@register.filter(name="cobalt_credits", is_safe=True)
def cobalt_credits(credits_amt):
    """Return formatted bridge credit number"""
    try:
        credits_amt = float(credits_amt)
    except ValueError:
        return None

    word = "credit" if credits_amt == 1.0 else "credits"

    try:
        if int(credits_amt) == credits_amt:
            credits_amt = int(credits_amt)
        ret = f"{credits_amt:,} {word}"
    except TypeError:
        ret = None

    return ret


@register.filter(name="cobalt_hide_email", is_safe=True)
def cobalt_hide_email(email):
    """Custom filter for email address which hides the address. Used by admin email viewer."""
    if not email:
        return None

    loc = email.find("@")
    last_fullstop = email.rfind(".")

    if loc and last_fullstop:
        hidden_email = "*" * len(email)
        hidden_email = hidden_email[:loc] + "@" + hidden_email[loc + 1 :]  # noqa: E203
        hidden_email = hidden_email[:last_fullstop] + email[last_fullstop:]
        return hidden_email
    else:
        return "*******************"


@register.filter(name="get_class")
def get_class(value):
    """Return class of object - used by search."""
    return value.__class__.__name__


@register.filter(name="cobalt_number", is_safe=True)
def cobalt_number(dollars):
    """Return number formatted with commas and 2 decimals"""
    dollars = round(float(dollars), 2)
    return "%s%s" % (intcomma(int(dollars)), ("%0.2f" % dollars)[-3:])


@register.filter(name="cobalt_currency", is_safe=True)
def cobalt_currency(dollars):
    """Return number formatted as currency"""
    dollars = round(float(dollars), 2)
    return "%s%s%s" % (
        GLOBAL_CURRENCY_SYMBOL,
        intcomma(int(dollars)),
        ("%0.2f" % dollars)[-3:],
    )


@register.simple_tag(name="cobalt_random_colour")
def cobalt_random_colour():
    """Return random bootstrap colour - useful for card headers from lists."""
    colours = ["primary", "info", "warning", "danger", "success", "rose"]

    return random.choice(colours)


@register.filter(name="cobalt_dict_key")
def cobalt_dict_key(my_dict, my_keyname):
    """Return value from key for an array in a template. Django doesn't do this out of the box"""

    try:
        return my_dict[my_keyname]
    except (KeyError, TypeError):
        return ""


@register.simple_tag
def cobalt_bs4_field(field, no_label=False):
    """Format a field for a standard Bootstrap 4 form element.

    Returns a form-group div with the field rendered inside
    Will include a label if the type of field suits it.

    This is a general tag to be used for any field. It tries
    to work out how to format the HTML based upon the type of field.

    use it per field so you can format the elements individually.

    e.g.

    <div class="col-6">{% cobalt_bs4_field form.field1 %}</div>
    <div class="col-6">{% cobalt_bs4_field form.field2 %}</div>
    """

    # class to add depends on type of field
    if field.widget_type == "checkbox":
        class_to_add = " form-check-input"
    else:
        class_to_add = " form-control"

    # Add our bootstrap class
    field_classes = field.field.widget.attrs.get('class', '')
    field_classes += class_to_add
    field.field.widget.attrs['class'] = field_classes

    # See if we want a label
    no_label_types = ["summernoteinplace", "select"]

    if no_label or  not field.label or field.widget_type in no_label_types:
        show_label = False
    else:
        show_label = True




    field_template = get_template("utils/cobalt_bs4_field/bs4_field.html")

    return field_template.render({"field": field, "show_label": show_label})
