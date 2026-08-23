from django.db import models
from django.utils.translation import gettext as _

from base.models import TimestampedModel

class SpaceState(TimestampedModel):
    is_open = models.BooleanField(default=False)

    def __str__(self):
        return _("Open") if self.is_open else _("Closed")

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Space State")
        verbose_name_plural = _("Space States")
