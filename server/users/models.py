from django.db import models
from django.core import validators
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from auditlog.registry import auditlog

from base.filters import (
    TOKEN_FILTER_CHOICES,
    PEOPLE_FILTER_CHOICES,
    MACHINE_FILTER_CHOICES,
)


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
    class TimeFormat(models.TextChoices):
        LOCALE = "locale", _("Locale Default")
        H12 = "12", _("12-hour")
        H24 = "24", _("24-hour")

    class DateFormat(models.TextChoices):
        LOCALE = "locale", _("Locale Default")
        DMY = "d.m.Y", _("Day-Month-Year (DD.MM.YYYY)")
        DMYS = "d.m.y", _("Day-Month-Year (DD.MM.YY)")
        MDY = "m/d/Y", _("Month-Day-Year (MM/DD/YYYY)")
        MDYS = "m/d/y", _("Month-Day-Year (MM/DD/YY)")
        YMD = "Y-m-d", _("Year-Month-Day (YYYY-MM-DD)")
        YSMD = "y-m-d", _("Year-Month-Day (YY-MM-DD)")
        WMDY = "M d, Y", _("Month Day, Year (Month DD, YYYY)")
        DWMY = "d M Y", _("Day Month Year (DD Month YYYY)")

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
        _("Language"), max_length=10, default="en", choices=settings.LANGUAGES
    )
    date_format = models.CharField(
        _("Date format"),
        max_length=10,
        choices=DateFormat.choices,
        default=DateFormat.LOCALE,
    )
    time_format = models.CharField(
        _("Time format"),
        max_length=10,
        choices=TimeFormat.choices,
        default=TimeFormat.LOCALE,
    )
    page_length = models.IntegerField(
        _("Page Length"),
        default=50,
        help_text=_("Number of items to show per page"),
        validators=[validators.MinValueValidator(1), validators.MaxValueValidator(300)],
    )
    default_token_filter = models.CharField(
        _("Default Token Filter"),
        max_length=20,
        default=TOKEN_FILTER_CHOICES["status"]["options"][0][0],
        choices=TOKEN_FILTER_CHOICES["status"]["options"],
    )
    default_people_filter = models.CharField(
        _("Default People Filter"),
        max_length=20,
        default=PEOPLE_FILTER_CHOICES["status"]["options"][0][0],
        choices=PEOPLE_FILTER_CHOICES["status"]["options"],
    )
    default_machines_filter = models.CharField(
        _("Default Machine Filter"),
        max_length=100,
        default=MACHINE_FILTER_CHOICES["status"]["options"][0][0],
        choices=MACHINE_FILTER_CHOICES["status"]["options"],
    )

    class ThemeMode(models.TextChoices):
        LIGHT = "light", _("Always Light")
        DARK = "dark", _("Always Dark")
        SYSTEM = "system", _("Follow System")

    theme_mode = models.CharField(
        max_length=10,
        choices=ThemeMode.choices,
        default=ThemeMode.SYSTEM,
        help_text=_(
            "Whether the interface always uses the light or dark theme below, or "
            "follows your device's setting."
        ),
    )
    light_theme = models.CharField(
        _("Light Theme"),
        max_length=10,
        choices=THEME_COLORS,
        default="default",
        help_text=_("Theme used in light mode."),
    )
    dark_theme = models.CharField(
        _("Dark Theme"),
        max_length=10,
        choices=THEME_COLORS,
        default="default",
        help_text=_("Theme used in dark mode."),
    )

    class NavStyle(models.TextChoices):
        NAVBAR = "navbar", _("Top Navigation Bar")
        SIDEBAR = "sidebar", _("Sidebar")

    nav_style = models.CharField(
        _("Navigation Style"),
        max_length=10,
        choices=NavStyle.choices,
        default=NavStyle.NAVBAR,
        help_text=_("Whether navigation is shown as a top bar or a sidebar."),
    )

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["email"]
        
    def __str__(self):
        return self.name


USER_WIDGETS = [
    ("token_counts", _("Token Counts")),
    ("people_counts", _("People Counts")),
    ("machine_counts", _("Machine Counts")),
    ("access_log_latest", _("Latest Access Log")),
    ("access_log_chart", _("Access Activity Chart")),
    ("audit_log_latest", _("Recent Audit Log")),
    ("pending_registration_requests", _("Pending Registration Requests")),
    ("space_status", _("Space Status")),
    ("machines_maintenance", _("Machines Needing Maintenance")),
]

WIDGET_PERMISSIONS = {
    "audit_log_latest": "tokens.view_token",
    "pending_registration_requests": "machines.add_machine",
    "machines_maintenance": "machines.view_machine",
}


class UserWidget(models.Model):
    user = models.ForeignKey(
        RFIDingUser, on_delete=models.CASCADE, related_name="widgets"
    )
    widget = models.CharField(
        max_length=100, choices=USER_WIDGETS, verbose_name=_("Widget")
    )
    position = models.IntegerField(default=-1, verbose_name=_("Position"))
    width = models.IntegerField(
        default=4,
        validators=[validators.MinValueValidator(2), validators.MaxValueValidator(12)],
        verbose_name=_("Width"),
        help_text=_("Width of the widget in columns (2-12)"),
    )
    settings = models.JSONField(default=dict, blank=True, verbose_name=_("Settings"))

    class Meta:
        verbose_name = _("User Widget")
        verbose_name_plural = _("User Widgets")
        ordering = ["user", "position"]

    @property
    def template(self):
        if self.widget == "token_counts" or self.widget == "people_counts":
            return "widgets/count.html"
        if self.widget == "machine_counts":
            return "widgets/machine_count.html"
        if self.widget == "access_log_latest":
            return "widgets/access_log_latest.html"
        if self.widget == "access_log_chart":
            return "widgets/access_log_chart.html"
        if self.widget == "audit_log_latest":
            return "widgets/audit_log_latest.html"
        if self.widget == "pending_registration_requests":
            return "widgets/pending_registration_requests.html"
        if self.widget == "space_status":
            return "widgets/space_status.html"
        if self.widget == "machines_maintenance":
            return "widgets/machines_maintenance.html"

    @property
    def title(self):
        if self.widget == "token_counts":
            return _("Tokens")
        if self.widget == "people_counts":
            return _("People")
        if self.widget == "machine_counts":
            return _("Machines")
        if self.widget == "access_log_latest":
            return _("Latest Access Log")
        if self.widget == "access_log_chart":
            return _("Access Activity")
        if self.widget == "audit_log_latest":
            return _("Recent Audit Log")
        if self.widget == "pending_registration_requests":
            return _("Pending Registration Requests")
        if self.widget == "space_status":
            return _("Space Status")
        if self.widget == "machines_maintenance":
            return _("Machines Needing Maintenance")

    @property
    def icon(self):
        if self.widget == "token_counts":
            return "radio-tower"
        if self.widget == "people_counts":
            return "users"
        if self.widget == "machine_counts":
            return "hard-drive"
        if self.widget == "access_log_latest":
            return "list"
        if self.widget == "access_log_chart":
            return "bar-chart-3"
        if self.widget == "audit_log_latest":
            return "history"
        if self.widget == "pending_registration_requests":
            return "cpu"
        if self.widget == "space_status":
            return "door-open"
        if self.widget == "machines_maintenance":
            return "wrench"


auditlog.register(RFIDingUser, exclude_fields=["password", "last_login"])
