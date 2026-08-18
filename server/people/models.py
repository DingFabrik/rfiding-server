from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from django.urls import reverse
from auditlog.registry import auditlog
from django.contrib.contenttypes.fields import GenericRelation

from base.models import TimestampedModel

from machines.models import Machine


class Person(TimestampedModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    email = models.EmailField(unique=True, verbose_name=_("Email address"))
    notes = models.TextField(null=True, blank=True, verbose_name=_("Notes"))
    member_id = models.IntegerField(
        null=True, blank=True, unique=True, verbose_name=_("Member ID")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_system_maintainer = models.BooleanField(
        default=False,
        help_text=_(
            "System maintainers have access to all machines in maintenance mode."
        ),
        verbose_name=_("Is System Maintainer"),
    )
    comments = GenericRelation("comments.Comment")

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ["member_id"]
        indexes = [
            models.Index(fields=["name"]),
        ]
        permissions = (
            ("change_instructor", _("Can manage instructors")),
            ("comment_person", _("Can comment on people")),
        )

    def get_absolute_url(self):
        return reverse("people:detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("people:update", kwargs={"pk": self.pk})

    def __str__(self):
        if self.member_id is None:
            return f"{self.name}"
        return f"{self.name} (#{self.member_id})"


PERMISSION_LEVELS = (
    ("if_space_open", _("Space is open")),
    ("always", _("Always")),
    ("never", _("Never")),
)


class Qualification(TimestampedModel):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="qualifications",
        verbose_name=_("Person"),
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="qualified_people",
        verbose_name=_("Machine"),
    )
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_LEVELS,
        default="if_space_open",
        verbose_name=_("Permission Level"),
    )
    comment = models.TextField(null=True, blank=True, verbose_name=_("Comment"))
    instructed_by = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="instructed_qualifications",
        verbose_name=_("Instructed By"),
    )

    is_instructor = models.BooleanField(
        default=False,
        help_text=_(
            "Instructors can give safety briefings and qualify other people on this machine."
        ),
        verbose_name=_("Is Instructor"),
    )
    is_maintainer = models.BooleanField(
        default=False,
        help_text=_(
            "Maintainers can perform maintenance on this machine and activate it in maintenance state."
        ),
        verbose_name=_("Is Maintainer"),
    )

    def __str__(self):
        return gettext(f"{self.person} qualified on {self.machine}")

    class Meta:
        verbose_name = _("Qualification")
        verbose_name_plural = _("Qualifications")
        permissions = (("qualify_person", _("Can manage qualifications")),)
        ordering = ["machine", "person__name"]


auditlog.register(Person, mask_fields=["email"], exclude_fields=["created", "updated"])
auditlog.register(Qualification, exclude_fields=["created", "updated"])
