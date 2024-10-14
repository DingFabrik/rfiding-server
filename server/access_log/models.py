from django.db import models
from django.utils.translation import gettext_lazy as _

LOG_TYPE_BOOTED = "booted"
LOG_TYPE_REGISTERED = "registered"
LOG_TYPE_ENABLED = "enabled"
LOG_TYPE_DISABLED = "disabled"

LOG_TYPES = (
    (LOG_TYPE_BOOTED, _("Booted")),
    (LOG_TYPE_ENABLED, _("Enabled")),
    (LOG_TYPE_DISABLED, _("Disabled")),
    (LOG_TYPE_REGISTERED, _("Registered")),
)


# Create your models here.
class AccessLog(models.Model):
    class Meta:
        verbose_name = _("Access Log")
        verbose_name_plural = _("Access Logs")

    timestamp = models.DateTimeField(auto_now_add=True)
    token = models.ForeignKey(
        "tokens.Token", on_delete=models.CASCADE, null=True, blank=True
    )
    machine = models.ForeignKey("machines.Machine", on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=LOG_TYPES)

    def __str__(self):
        return f"{self.timestamp} {self.token} {self.machine}"
