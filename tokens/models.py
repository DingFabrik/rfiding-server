from django.db import models
from django.urls import reverse
from django.conf import settings
from base.models import TimestampedModel
from django.utils.translation import gettext_lazy as _

from machines.models import Machine
from people.models import Person

TOKEN_STATUS = (
    ("unknown", "unknown"),
    ("archived", "Archived"),
    ("assigned", "Assigned"),
)

class Token(TimestampedModel):
    serial = models.CharField(max_length=20, db_index=True)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.serial}"

    def get_absolute_url(self):
        return reverse("tokens:detail", kwargs={"pk": self.pk})

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")
        ordering = ["pk"]

class UnknownToken(TimestampedModel):
    serial = models.CharField(max_length=20)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.serial}"