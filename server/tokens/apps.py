from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TokensConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tokens"
    verbose_name = _("Tokens")
