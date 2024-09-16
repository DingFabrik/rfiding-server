from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from auditlog.registry import auditlog

from base.models import TimestampedModel

from machines.models import Machine


class Person(TimestampedModel):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    notes = models.TextField(null=True, blank=True)
    member_id = models.IntegerField(null=True, blank=True, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ["pk"]
        permissions = (("change_instructor", "Can manage instructors"),)

    def get_absolute_url(self):
        return reverse("people:detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("people:update", kwargs={"pk": self.pk})

    def __str__(self):
        if self.member_id is None:
            return f"{self.name}"
        return f"{self.name} (#{self.member_id})"


PERMISSION_LEVELS = (
    ("if_space_open", _("If space is open")),
    ("always", _("Always")),
    ("never", _("Never")),
)


class Qualification(TimestampedModel):
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="qualifications"
    )
    machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="qualified_people"
    )
    permission_level = models.CharField(
        max_length=20, choices=PERMISSION_LEVELS, default="if_space_open"
    )
    comment = models.TextField(null=True, blank=True)
    instructed_by = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="instructed_qualifications",
    )

    def __str__(self):
        return f"{self.person} qualified on {self.machine}"

    class Meta:
        verbose_name = _("Qualification")
        verbose_name_plural = _("Qualifications")
        permissions = (("qualify_person", "Can manage qualifications"),)


class Instructor(TimestampedModel):
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="can_instruct"
    )
    machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="instructors"
    )
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.person} is instructor on {self.machine}"

    class Meta:
        verbose_name = _("Instructor")
        verbose_name_plural = _("Instructors")

auditlog.register(Person, mask_fields=["email"], exclude_fields=["created", "updated"])
auditlog.register(Qualification, exclude_fields=["created", "updated"])
auditlog.register(Instructor, exclude_fields=["created", "updated"])