from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HolidaysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "holidays"
    verbose_name = _("Holidays")
