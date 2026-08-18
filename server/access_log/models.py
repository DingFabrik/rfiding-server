from django.db import models
from django.utils.translation import gettext_lazy as _

LOG_TYPE_BOOTED = "booted"
LOG_TYPE_REGISTERED = "registered"
LOG_TYPE_ENABLED = "enabled"
LOG_TYPE_DISABLED = "disabled"
LOG_TYPE_UNSUCCESSFUL = "unsuccessful"

LOG_TYPES = (
    (LOG_TYPE_BOOTED, _("Booted")),
    (LOG_TYPE_REGISTERED, _("Registered")),
    (LOG_TYPE_ENABLED, _("Enabled")),
    (LOG_TYPE_DISABLED, _("Disabled")),
    (LOG_TYPE_UNSUCCESSFUL, _("Unsuccessful")),
)


class AccessLog(models.Model):
    class Meta:
        verbose_name = _("Access Log")
        verbose_name_plural = _("Access Logs")
        ordering = ("-timestamp",)

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Timestamp"))
    token = models.ForeignKey(
        "tokens.Token",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Token"),
    )
    machine = models.ForeignKey(
        "machines.Machine", on_delete=models.CASCADE, verbose_name=_("Machine")
    )
    enabled_duration = models.DurationField(
        null=True,
        blank=True,
        verbose_name=_("Enabled Duration"),
        help_text=_("Duration the machine was enabled for this access. Only set for 'disabled' events."),
    )
    type = models.CharField(max_length=20, choices=LOG_TYPES, verbose_name=_("Type"))

    def __str__(self):
        return f"{self.timestamp} {self.token} {self.machine}"
