from django.urls import reverse
from django.utils.translation import gettext_lazy as _

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
            "has_permission": request.user.has_perm("people.view_person"),
            "active": request.resolver_match.app_name == "people",
        },
        {
            "name": _("Machines"),
            "url": reverse("machines:list"),
            "icon": "hdd",
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
        """{
            "name": _("Firmware"),
            "url": reverse("firmware:list"),
            "icon": "microchip",
            "has_permission": request.user.has_perm("firmware.view_firmware"),
            "active": request.resolver_match.app_name == "firmware",
        },"""
    ]
    return {"menu": menu}