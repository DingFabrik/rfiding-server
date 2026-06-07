from django.db import models
from django.urls import reverse
from base.models import TimestampedModel
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from django.contrib.contenttypes.fields import GenericRelation

from machines.models import Machine
from people.models import Person

TOKEN_STATUS = (
    ("unknown", _("Unknown")),
    ("archived", _("Archived")),
    ("assigned", _("Assigned")),
)

logger = logging.getLogger(__name__)


class TokenType(TimestampedModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    label_prefix = models.CharField(max_length=10, blank=True, verbose_name=_("Label Prefix"))
    label_id_padding = models.IntegerField(default=0, verbose_name=_("Label ID Padding"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    def __str__(self):
        return f"{self.name}"

    def format_label_id(self, label_id):
        if not label_id:
            return None
        return f"{self.label_prefix}{label_id:0{self.label_id_padding}d}"

    class Meta:
        verbose_name = _("Token Type")
        verbose_name_plural = _("Token Types")
        ordering = ["name"]


class Token(TimestampedModel):
    serial = models.CharField(max_length=20, db_index=True, verbose_name=_("Serial"))
    person = models.ForeignKey(Person, on_delete=models.CASCADE, verbose_name=_("Person"))
    purpose = models.CharField(max_length=100, verbose_name=_("Purpose"))
    type = models.ForeignKey(TokenType, on_delete=models.CASCADE, null=True, verbose_name=_("Type"))
    label_id = models.IntegerField(null=True, blank=True, verbose_name=_("Label ID"))
    notes = models.TextField(null=True, blank=True, verbose_name=_("Notes"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    archived = models.DateTimeField(null=True, blank=True, verbose_name=_("Archived"))
    comments = GenericRelation("comments.Comment")

    def __str__(self):
        return f"{self.serial}"

    def get_absolute_url(self):
        return reverse("tokens:detail", kwargs={"pk": self.pk})

    def format_label(self):
        if self.type and self.label_id:
            return self.type.format_label_id(self.label_id)
        return self.label_id or self.purpose

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")
        ordering = ["serial"]
        unique_together = ("serial", "archived")
        indexes = [
            models.Index(fields=["serial"]),
        ]


class UnknownToken(TimestampedModel):
    serial = models.CharField(max_length=20, blank=False, verbose_name=_("Serial"))
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, verbose_name=_("Machine"))

    def __str__(self):
        return f"{self.serial}"

    class Meta:
        verbose_name = _("Unknown Token")
        verbose_name_plural = _("Unknown Tokens")
        ordering = ["-created"]


class BlacklistedToken(TimestampedModel):
    serial = models.CharField(max_length=20, verbose_name=_("Serial"))

    def __str__(self):
        return f"{self.serial}"

    class Meta:
        verbose_name = _("Blacklisted Token")
        verbose_name_plural = _("Blacklisted Tokens")
        ordering = ["serial"]


channel_layer = get_channel_layer()


@receiver(post_save, sender=UnknownToken)
def signal_unknowntoken_saved(sender, instance, created, **kwargs):
    logger.info(
        "Unknown token used\nToken ID: %s\nMachine: %s",
        instance.serial,
        instance.machine,
    )
    if created:
        async_to_sync(channel_layer.group_send)(
            "unknown_tokens", {"type": "unknown_token_list_changed"}
        )


auditlog.register(Token, exclude_fields=["created", "updated"])
auditlog.register(TokenType, exclude_fields=["created", "updated"])
