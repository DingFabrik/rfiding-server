from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccessLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "access_log"
    verbose_name = _("Access Log")
