from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MachinesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "machines"
    verbose_name = _("Machines")
