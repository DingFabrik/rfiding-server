from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings as SETTINGS

def version_processor(request):
    return { "rfiding_version": SETTINGS.VERSION }

def menu_processor(request):
    menu = [
        {
            "name": _("Tokens"),
            "url": reverse("tokens:list"),
            "icon": "broadcast",
            "has_permission": request.user.has_perm("tokens.view_token"),
            "active": request.resolver_match.app_name == "tokens",
        },
        {
            "name": _("People"),
            "url": reverse("people:list"),
            "icon": "people",
            "active_icon": "people-fill",
            "has_permission": request.user.has_perm("people.view_person"),
            "active": request.resolver_match.app_name == "people",
        },
        {
            "name": _("Machines"),
            "url": reverse("machines:list"),
            "icon": "hdd",
            "active_icon": "hdd-fill",
            "has_permission": request.user.has_perm("machines.view_machine"),
            "active": request.resolver_match.app_name == "machines",
        },
        {
            "name": _("Access Log"),
            "url": reverse("access_log:list"),
            "icon": "card-list",
            "has_permission": request.user.has_perm("access_log.view_accesslog"),
            "active": request.resolver_match.app_name == "access_log",
        },
    ]
    
    side_menu = [
        {
            "name": _("Audit Log"),
            "url": reverse("auditlog"),
            "icon": "person-lines-fill",
            "has_permission": request.user.is_superuser,
            "active": request.resolver_match.url_name == "auditlog",
        },
        """{
            "name": _("Firmware"),
            "url": reverse("firmware:list"),
            "icon": "microchip",
            "has_permission": request.user.has_perm("firmware.view_firmware"),
            "active": request.resolver_match.app_name == "firmware",
        },""",
        {
            "name": _("Users"),
            "url": reverse("users:list"),
            "icon": "person-badge",
            "active_icon": "person-badge-fill",
            "has_permission": request.user.has_perm("users.view_rfidinguser"),
            "active": request.resolver_match.app_name == "users" and request.resolver_match.url_name != "profile",
        },
                {
            "name": _("Groups"),
            "url": reverse("users:groups:list"),
            "icon": "people",
            "active_icon": "people-fill",
            "has_permission": request.user.has_perm("auth.view_group"),
            "active": request.resolver_match.app_name == "groups",
        },
        {
            "name": _("Blacklisted Tokens"),
            "url": reverse("tokens:blacklisted"),
            "icon": "broadcast",
            "has_permission": request.user.has_perm("auth.view_blacklistedtoken"),
            "active": request.resolver_match.url_name == "blacklisted",
        },
        {
            "name": _("Token Types"),
            "url": reverse("tokens:types:list"),
            "icon": "broadcast",
            "has_permission": request.user.has_perm("auth.view_tokentype"),
            "active": request.resolver_match.url_name == "types",
        },
        {
            "name": _("Django Admin"),
            "url": reverse("admin:index"),
            "icon": "person-gear",
            "active_icon": "person-gear-fill",
            "has_permission": request.user.is_staff,
        },
        {
            "name": _("About"),
            "url": reverse("about"),
            "icon": "info-circle",
            "active_icon": "info-circle-fill",
            "has_permission": True,
            "active": request.resolver_match.url_name == "about",
        },
        {
            "type": "divider"
        },
        {
            "name": _("Settings"),
            "url": reverse("users:profile"),
            "icon": "gear",
            "active_icon": "gear-fill",
            "has_permission": True,
            "active": request.resolver_match.url_name == "profile",
        },
    ]
    return {"menu": menu, "side_menu": side_menu}
