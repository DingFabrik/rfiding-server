from django.db import models
from django.urls import reverse
from base.models import TimestampedModel
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog

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
    notes = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    archived = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.serial}"

    def get_absolute_url(self):
        return reverse("tokens:detail", kwargs={"pk": self.pk})

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")
        ordering = ["pk"]
        unique_together = ("serial", "archived")


class UnknownToken(TimestampedModel):
    serial = models.CharField(max_length=20)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.serial}"

auditlog.register(Token, exclude_fields=["created", "updated"])