"""values set in here are passed to every template"""

from django.conf import settings
from notifications.views.user import get_notifications_for_user
from events.views.core import get_basket_for_user
from support.helpdesk import get_tickets
from .version import COBALT_VERSION
from rbac.core import rbac_show_admin
from organisations.views import general as orgs


def global_settings(request):

    if request.user.is_anonymous:
        notifications = {}
        notification_count = 0
        basket_items = 0
        show_admin_on_template = False
        support_tickets = False
        club_staff = False
    else:
        (notification_count, notifications) = get_notifications_for_user(request.user)
        basket_items = get_basket_for_user(request.user)
        show_admin_on_template = rbac_show_admin(request)
        support_tickets = get_tickets(request.user)
        club_staff = orgs.club_staff(request.user)

    return {
        "notification_count": notification_count,
        "notifications": notifications,
        "basket_items": basket_items,
        "show_admin_on_template": show_admin_on_template,
        "support_tickets": support_tickets,
        "club_staff": club_staff,
        "COBALT_VERSION": COBALT_VERSION,
        "COBALT_HOSTNAME": settings.COBALT_HOSTNAME,
        "BRIDGE_CREDITS": settings.BRIDGE_CREDITS,
        "GLOBAL_ORG": settings.GLOBAL_ORG,
        "GLOBAL_TITLE": settings.GLOBAL_TITLE,
        "GLOBAL_CONTACT": settings.GLOBAL_CONTACT,
        "GLOBAL_ABOUT": settings.GLOBAL_ABOUT,
        "GLOBAL_COOKIES": settings.GLOBAL_COOKIES,
        "GLOBAL_MPSERVER": settings.GLOBAL_MPSERVER,
        "GLOBAL_PRODUCTION": settings.GLOBAL_PRODUCTION,
        "GLOBAL_TEST": settings.GLOBAL_TEST,
        "GLOBAL_PRIVACY": settings.GLOBAL_PRIVACY,
        "GLOBAL_CURRENCY_SYMBOL": settings.GLOBAL_CURRENCY_SYMBOL,
        "GLOBAL_CURRENCY_NAME": settings.GLOBAL_CURRENCY_NAME,
        "AUTO_TOP_UP_MAX_AMT": settings.AUTO_TOP_UP_MAX_AMT,
        "AUTO_TOP_UP_MIN_AMT": settings.AUTO_TOP_UP_MIN_AMT,
        "AUTO_TOP_UP_LOW_LIMIT": settings.AUTO_TOP_UP_LOW_LIMIT,
        "RBAC_EVERYONE": settings.RBAC_EVERYONE,
        "TBA_PLAYER": settings.TBA_PLAYER,
        "NEW_RELIC_APP_ID": settings.NEW_RELIC_APP_ID,
        "XERO_TENANT_NAME": settings.XERO_TENANT_NAME,
        "MAINTENANCE_MODE": settings.MAINTENANCE_MODE,
    }
