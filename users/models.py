from django.db import models
from django.core import validators
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from auditlog.registry import auditlog

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


THEME_COLORS = (
    ("default", _("Default (Blue)")),
    ("purple", _("Purple")),
    ("red", _("Red")),
    ("orange", _("Orange")),
    ("yellow", _("Yellow")),
    ("green", _("Green")),
    ("pink", _("Pink")),
    ("teal", _("Teal")),
    ("cyan", _("Cyan")),
)

class RFIDingUser(AbstractUser):
    USERNAME_FIELD = "email"
    username = None
    first_name = None
    last_name = None
    email = models.EmailField(
        _("E-Mail Address"), unique=True
    )  # changes email to unique and blank to false
    name = models.CharField(_("Name"), max_length=150, blank=True)
    REQUIRED_FIELDS = []

    language = models.CharField(
        _("Langauge"), max_length=10, default="en", choices=settings.LANGUAGES
    )
    page_length = models.IntegerField(
        _("Page Length"),
        default=50,
        help_text=_("Number of items to show per page"),
        validators=[validators.MinValueValidator(1), validators.MaxValueValidator(300)],
    )

    theme_mode = models.CharField(max_length=10, choices=[("light", _("Light")), ("dark", _("Dark")), ("auto", _("Auto"))], default="auto")
    theme = models.CharField(max_length=10, choices=THEME_COLORS, default="default")

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

auditlog.register(RFIDingUser, exclude_fields=["password", "last_login"])