from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SpaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "space"
    verbose_name = _("Space")
