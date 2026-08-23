import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from django.urls import reverse
from auditlog.registry import auditlog
from django.contrib.contenttypes.fields import GenericRelation

from base.models import TimestampedModel

from machines.models import Machine
from .conf import PERSON_DEFAULT_LANGUAGE, PERSON_DETAIL_KEY_VALID_HOURS

QUALIFICATION_EXPIRY_WARNING_DAYS = (
    settings.QUALIFICATION_EXPIRY_WARNING_DAYS
    if hasattr(settings, "QUALIFICATION_EXPIRY_WARNING_DAYS")
    else 7
)

class Person(TimestampedModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    email = models.EmailField(unique=True, null=True, verbose_name=_("E-Mail address"))
    slack_email = models.CharField(max_length=100, unique=True, verbose_name=_("Slack e-mail"),
                                    null=True, blank=True,
                                    help_text=_("Slack account e-mail for sending notifications."))
    slack_conversation_id = models.CharField(max_length=100, unique=True, verbose_name=_("Slack conversation ID"),
                                             null=True, blank=True)
    language = models.CharField(
        _("Language"), max_length=10, default=PERSON_DEFAULT_LANGUAGE, choices=settings.LANGUAGES,
        help_text=_("Preferred language for notifications and emails.")
    )
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
    
    detail_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("Detail Key"),
        help_text=_(
            "Random key granting access to this person's self-service detail page. "
            "Valid until Detail Key Expires At."
        ),
    )
    detail_key_expires_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Detail Key Expires At")
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

    def generate_detail_key(self):
        """Generate a new self-service detail page key, valid for PERSON_DETAIL_KEY_VALID_HOURS."""
        self.detail_key = secrets.token_urlsafe(32)
        self.detail_key_expires_at = timezone.now() + timedelta(
            hours=PERSON_DETAIL_KEY_VALID_HOURS
        )
        self.save(update_fields=["detail_key", "detail_key_expires_at"])
        return self.detail_key

    def get_detail_url(self):
        return reverse("people:public-detail", kwargs={"key": self.detail_key})

    @property
    def detail_key_valid(self):
        return (
            bool(self.detail_key)
            and self.detail_key_expires_at is not None
            and self.detail_key_expires_at > timezone.now()
        )

    def __str__(self):
        if self.member_id is None:
            return f"{self.name}"
        return f"{self.name} (#{self.member_id})"


PERMISSION_LEVELS = (
    ("if_space_open", _("If Open")),
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

    last_used = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Used"),
        help_text=_("When this qualification was last used to access the machine."),
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expires At"),
        help_text=_(
            "When this qualification will expire if it is not used again. Empty if "
            "expiration is disabled for this machine."
        ),
    )
    expired = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expired"),
        help_text=_("When this qualification expired."),
    )
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Notified At"),
        help_text=_(
            "When the person was last notified of the upcoming expiration. Clear to "
            "send a notification again."
        ),
    )

    def compute_expires_at(self):
        """Return when this qualification would expire if not used again, or None if disabled."""
        if self.last_used is None:
            days = self.machine.qualification_expiry_unused_days
            base = self.created
        else:
            days = self.machine.qualification_expiry_used_days
            base = self.last_used
        if not days:
            return None
        return base + timedelta(days=days)

    def mark_used(self):
        self.last_used = timezone.now()
        self.expires_at = self.compute_expires_at()
        self.notified_at = None
        self.save(update_fields=["last_used", "expires_at", "notified_at"])

    @property
    def expires_soon(self):
        if self.expired is not None or self.expires_at is None:
            return False
        return self.expires_at <= timezone.now() + timedelta(
            days=QUALIFICATION_EXPIRY_WARNING_DAYS
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
