from django.urls import reverse
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy as _
from django.conf import settings as SETTINGS

from base.app_icons import APP_ICONS
from users.models import RFIDingUser


def version_processor(request):
    return {"rfiding_version": SETTINGS.VERSION}


def _build_menus(request):
    match = request.resolver_match
    app_name = match.app_name if match else None
    url_name = match.url_name if match else None
    namespace = match.namespace if match else None

    menu = [
        {
            "name": _("Tokens"),
            "url": reverse("tokens:list"),
            "icon": APP_ICONS["tokens"],
            "has_permission": request.user.has_perm("tokens.view_token"),
            "active": app_name == "tokens" and url_name != "blacklisted",
        },
        {
            "name": _("People"),
            "url": reverse("people:list"),
            "icon": APP_ICONS["people"],
            "has_permission": request.user.has_perm("people.view_person"),
            "active": app_name == "people",
        },
        {
            "name": _("Machines"),
            "url": reverse("machines:list"),
            "icon": APP_ICONS["machines"],
            "has_permission": request.user.has_perm("machines.view_machine"),
            "active": app_name == "machines",
        },
        {
            "name": _("Access Log"),
            "url": reverse("access_log:list"),
            "icon": APP_ICONS["access_log"],
            "has_permission": request.user.has_perm("access_log.view_accesslog"),
            "active": app_name == "access_log",
        },
        {
            "name": _("Statistics"),
            "url": reverse("statistics"),
            "icon": "bar-chart-3",
            "has_permission": request.user.has_perm("access_log.view_accesslog"),
            "active": url_name == "statistics",
        },
    ]

    side_menu = [
        {
            "name": _("Audit Log"),
            "url": reverse("auditlog"),
            "icon": "history",
            "has_permission": request.user.is_superuser,
            "active": url_name == "auditlog",
        },
        {
            "name": _("Users"),
            "url": reverse("users:list"),
            "icon": APP_ICONS["users"],
            "has_permission": request.user.has_perm("users.view_rfidinguser"),
            "active": app_name == "users"
            and url_name != "profile",
        },
        {
            "name": _("Groups"),
            "url": reverse("users:groups:list"),
            "icon": APP_ICONS["groups"],
            "has_permission": request.user.has_perm("auth.view_group"),
            "active": namespace == "users:groups",
        },
        {
            "name": _("Holidays"),
            "url": reverse("holidays:list"),
            "icon": APP_ICONS["holidays"],
            "has_permission": request.user.has_perm("holidays.view_holiday"),
            "active": app_name == "holidays",
        },
        {
            "name": _("Locations"),
            "url": reverse("locations:list"),
            "icon": APP_ICONS["locations"],
            "has_permission": request.user.has_perm("locations.view_location"),
            "active": app_name == "locations",
        },
        {
            "name": _("Blacklisted Tokens"),
            "url": reverse("tokens:blacklisted"),
            "icon": APP_ICONS["tokens"],
            "has_permission": request.user.has_perm("tokens.view_blacklistedtoken"),
            "active": url_name == "blacklisted",
        },
        {
            "name": _("Token Types"),
            "url": reverse("tokens:types:list"),
            "icon": APP_ICONS["tokens"],
            "has_permission": request.user.has_perm("tokens.view_tokentype"),
            "active": namespace == "tokens:types",
        },
        {
            "name": _("Django Admin"),
            "url": reverse("admin:index"),
            "icon": "user-cog",
            "has_permission": request.user.is_staff,
        },
        {
            "name": _("About"),
            "url": reverse("about"),
            "icon": "info",
            "has_permission": True,
            "active": url_name == "about",
        },
        {"type": "divider"},
        {
            "name": _("Settings"),
            "url": reverse("users:profile"),
            "icon": "settings",
            "has_permission": True,
            "active": url_name == "profile",
        },
    ]
    return {"menu": menu, "side_menu": side_menu}


def menu_processor(request):
    menus = SimpleLazyObject(lambda: _build_menus(request))
    return {
        "menu": SimpleLazyObject(lambda: menus["menu"]),
        "side_menu": SimpleLazyObject(lambda: menus["side_menu"]),
        "nav_style": SimpleLazyObject(
            lambda: request.user.nav_style
            if request.user.is_authenticated
            else RFIDingUser.NavStyle.NAVBAR
        ),
    }
