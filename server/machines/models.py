import datetime
import uuid
from django.db import models
from base.models import TimestampedModel
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from auditlog.registry import auditlog
from datetime import timedelta
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import formats

from machines.fields import WeekdayFormField


def is_str(obj):
    return isinstance(obj, str)


class WeekdayField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 20
        super(WeekdayField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        return super(WeekdayField, self).formfield(
            form_class=WeekdayFormField, **kwargs
        )

    def to_python(self, value):
        if is_str(value):
            if value:
                value = [int(x) for x in value.strip("[]").split(",") if x]
            else:
                value = []
        return value

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        return ",".join([str(x) for x in value or []])


class Machine(TimestampedModel):
    class SupportedChips(models.TextChoices):
        ESP32 = "esp32", _("ESP32")
        ESP8266 = "esp8266", _("ESP8266")
        ESP32S2 = "esp32s2", _("ESP32-S2")
        ESP32C3 = "esp32c3", _("ESP32-C3")
        ESP32S3 = "esp32s3", _("ESP32-S3")

    class MachineType(models.TextChoices):
        PRIMARY = "primary", _("Primary")
        SECONDARY = "secondary", _("Secondary")
        LOCK = "lock", _("Lock")
        LOCK_GROUP = "lock_group", _("Locker")
        COMPARTMENT = "compartment", _("Compartment")

    class MachineStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        MAINTENANCE = "maintenance", _("Maintenance")

    name = models.CharField(max_length=100, verbose_name=_("Name"))
    type = models.CharField(
        max_length=100,
        choices=MachineType.choices,
        default=MachineType.PRIMARY,
        verbose_name=_("Type"),
        help_text=_("Type of machine. Primary machines are the main machines."),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
        verbose_name=_("Parent Machine"),
        help_text=_("If this is a compartment in a locker, select the locker here."),
    )
    compartment_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("Compartment ID"),
        help_text=_("Identifier for the compartment in a locker."),
    )
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        related_name="machines",
        null=True,
        blank=True,
        verbose_name=_("Location"),
    )
    state = models.CharField(
        max_length=20, default=MachineStatus.ACTIVE, choices=MachineStatus.choices, verbose_name=_("State")
    )
    needs_qualification = models.BooleanField(
        default=True,
        verbose_name=_("Needs Qualification"),
        help_text=_("If disabled, any active user can access this machine."),
    )

    mac_address = models.CharField(
        max_length=17,
        db_index=True,
        null=True,
        blank=True,
        verbose_name=_("MAC Address"),
    )
    hostname = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Hostname")
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("IP-Address")
    )
    encryption_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_("Encryption Key"),
        help_text=_(
            "64 character encryption key for secure communication with the machine."
        ),
    )
    api_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text=_("API Key for authenticated when the machine accesses the API."),
        verbose_name=_("API Key"),
    )
    chip = models.CharField(
        verbose_name=_("Chip"),
        max_length=100,
        default=SupportedChips.ESP32,
        choices=SupportedChips.choices,
    )
    firmware_version = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Firmware Version")
    )

    log_booted = models.BooleanField(
        default=True, verbose_name=_("Log Booted"), help_text=_("Log boot events")
    )
    log_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Log Enabled"),
        help_text=_("Log successful unlock events"),
    )
    log_disabled = models.BooleanField(
        default=False,
        verbose_name=_("Log Disabled"),
        help_text=_("Log when machine is disabled again"),
    )
    log_unsuccessful = models.BooleanField(
        default=False,
        verbose_name=_("Log Unsuccessful"),
        help_text=_("Log unsuccessful unlock attempts"),
    )

    runtimer = models.DurationField(
        default=timedelta(),
        verbose_name=_("Run Timer"),
        help_text=_("Time until the machine is locked again when it is not active."),
    )
    min_power = models.IntegerField(
        default=10,
        verbose_name=_("Minimum Power"),
        help_text=_(
            "Minimum power consumption in watts for the machine to be considered active."
        ),
    )
    control_parameter = models.CharField(max_length=100, null=True, blank=True)
    display_time_countdown = models.BooleanField(
        default=True,
        verbose_name=_("Display Time Countdown"),
        help_text=_(
            "Whether the machine displays the time remaining until it locks again when it is unlocked but not active."
        ),
    )
    display_power_consumption = models.BooleanField(
        default=True,
        verbose_name=_("Display Power Consumption"),
        help_text=_("If the machine displays the power consumption when it is active."),
    )
    link_relays = models.BooleanField(
        default=False,
        verbose_name=_("Link Relays"),
        help_text=_(
            "If set, the machine relays are linked and the secondary relay is activated together with the primary relay."
        ),
    )
    allowed_on_holidays = models.BooleanField(
        default=True,
        verbose_name=_("Allowed on Holidays"),
        help_text=_("If set, the machine can be used on holidays."),
    )
    
    maintenance_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Maintenance Message"),
        help_text=_("Reason why the machine is in maintenance mode."),
    )

    qualification_expiry_unused_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Qualification Expiry (Unused)"),
        help_text=_(
            "Number of days after which a qualification for this machine expires if it "
            "has never been used. Leave empty to disable this expiration."
        ),
    )
    qualification_expiry_used_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Qualification Expiry (After Use)"),
        help_text=_(
            "Number of days after its last use after which a qualification for this "
            "machine expires. Leave empty to disable this expiration."
        ),
    )

    comments = GenericRelation("comments.Comment")

    class Meta:
        verbose_name = _("Machine")
        verbose_name_plural = _("Machines")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["mac_address"]),
            models.Index(fields=["name"]),
        ]
        permissions = (
            ("view_machine_state", _("View Machine State")),
            ("view_machine_logs", _("View Machine Logs")),
            ("send_machine_commands", _("Send Machine Commands")),
            ("comment_machine", _("Can comment on machines")),
        )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.mac_address:
            self.mac_address = self.mac_address.lower()
        super().save(*args, **kwargs)

    @property
    def has_api(self):
        return (
            self.encryption_key is not None
            and len(self.encryption_key) > 0
            and self.ip_address is not None
        )

    @property
    def instructors(self):
        return self.qualified_people.filter(is_instructor=True)

    @property
    def maintainers(self):
        return self.qualified_people.filter(is_maintainer=True)

    @property
    def is_active(self):
        return self.state == Machine.MachineStatus.ACTIVE

    def get_absolute_url(self):
        return reverse("machines:detail", kwargs={"pk": self.pk})

    def is_now_valid_time(self):
        if not self.times.all():
            return True
        now = datetime.datetime.now()
        return (
            self.times.filter(weekdays__contains=now.weekday())
            .filter(start_time__lte=now.time())
            .filter(end_time__gte=now.time())
            .exists()
        )

    @staticmethod
    def get_valid_end_time_for_times(times):
        if not times.exists():
            return datetime.time(23, 59, 59)
        now = datetime.datetime.now()
        match = (
            times.filter(weekdays__contains=now.weekday())
            .filter(start_time__lte=now.time())
            .filter(end_time__gte=now.time())
            .order_by("end_time")
            .first()
        )
        if match is None:
            return None
        return match.end_time

    @staticmethod
    def get_valid_end_time_for_machine(machine_id):
        query = MachineTime.objects.filter(machine_id=machine_id)
        return Machine.get_valid_end_time_for_times(query)

    def get_valid_end_time(self):
        return Machine.get_valid_end_time_for_times(self.times)


class MachineTime(TimestampedModel):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="times")
    weekdays = WeekdayField(verbose_name=_("Weekdays"))
    start_time = models.TimeField(verbose_name=_("Start Time"))
    end_time = models.TimeField(verbose_name=_("End Time"))

    def __str__(self):
        return f"{self.get_weekdays_display()} {formats.time_format(self.start_time) if isinstance(self.start_time, datetime.time) else self.start_time} - {formats.time_format(self.end_time) if isinstance(self.end_time, datetime.time) else self.end_time}"

    def get_weekdays_display(self):
        if not self.weekdays or len(self.weekdays) == 7:
            return _("Everyday")
        if self.weekdays == [0, 1, 2, 3, 4]:
            return _("Weekdays")
        if self.weekdays == [5, 6]:
            return _("Weekends")
        days = []
        for day in self.weekdays:
            if day == 0:
                days.append(_("Monday"))
            elif day == 1:
                days.append(_("Tuesday"))
            elif day == 2:
                days.append(_("Wednesday"))
            elif day == 3:
                days.append(_("Thursday"))
            elif day == 4:
                days.append(_("Friday"))
            elif day == 5:
                days.append(_("Saturday"))
            elif day == 6:
                days.append(_("Sunday"))
        return ", ".join(str(day) for day in days)


class MachineRegistrationRequest(TimestampedModel):
    mac_address = models.CharField(max_length=17, db_index=True, verbose_name=_("MAC Address"))
    hostname = models.CharField(max_length=100, verbose_name=_("Hostname"))
    ip_address = models.GenericIPAddressField(verbose_name=_("IP-Address"))

    class Meta:
        verbose_name = _("Registration Request")
        verbose_name_plural = _("Registration Requests")
        ordering = ["-created"]

    def __str__(self):
        return self.mac_address


class MachineControlKey(TimestampedModel):
    machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="control_keys",
        verbose_name=_("Machine"),
    )
    key = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_("Key"))
    purpose = models.CharField(max_length=100, verbose_name=_("Purpose"))
    last_used = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Used"))

    class Meta:
        verbose_name = _("Control Key")
        verbose_name_plural = _("Control Keys")
        ordering = ["-created"]

    def __str__(self):
        return self.purpose


class MachineConnection(TimestampedModel):
    primary_machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="as_primary_machine", verbose_name=_("Primary Machine")
    )
    secondary_machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="as_secondary_machine", verbose_name=_("Secondary Machine")
    )

    class Meta:
        verbose_name = _("Machine Connection")
        verbose_name_plural = _("Machine Connections")
        ordering = ["-created"]

    def __str__(self):
        return f"{self.primary_machine} -> {self.secondary_machine}"


auditlog.register(Machine, exclude_fields=["created", "updated"])
auditlog.register(MachineTime, exclude_fields=["created", "updated"])
auditlog.register(MachineControlKey, exclude_fields=["created", "updated", "last_used"])
auditlog.register(MachineConnection, exclude_fields=["created", "updated"])
