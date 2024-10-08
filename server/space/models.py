from django.db import models
from django.utils.translation import gettext as _

from base.models import TimestampedModel


# Create your models here.
class SpaceState(TimestampedModel):
    is_open = models.BooleanField(default=False)

    def __str__(self):
        return _("Open") if self.is_open else _("Closed")

    class Meta:
        ordering = ["-created"]
