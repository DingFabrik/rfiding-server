import datetime
import uuid
from django.db import models
from base.models import TimestampedModel
from django.utils.translation import gettext as _
from django.urls import reverse
from auditlog.registry import auditlog
from django.conf import settings
from datetime import timedelta

from machines.fields import WeekdayFormField
from .client_modules import (
    ACCESS_CONTROL_MODULES,
    STATUS_DISPLAY_MODULES,
    ACTOR_MODULES,
)

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


ENFORCE_API_KEYS = (
    settings.ENFORCE_API_KEYS if hasattr(settings, "ENFORCE_API_KEYS") else False
)


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


    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=100, choices=MachineType.choices, default=MachineType.PRIMARY,
        help_text=_("Type of machine. Primary machines are the main machines."),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
        help_text=_("If this is a compartment in a locker, select the locker here."),
    )
    compartment_id = models.CharField(max_length=20, null=True, blank=True)
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        related_name="machines",
        null=True,
        blank=True,
    )
    state = models.CharField(max_length=20, default=MachineStatus.ACTIVE, choices=MachineStatus.choices)
    needs_qualification = models.BooleanField(
        default=True,
        help_text=_("If disabled, any active user can access this machine."),
    )

    mac_address = models.CharField(max_length=17, db_index=True, null=True, blank=True)
    hostname = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    encryption_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text=_(
            "64 character encryption key for secure communication with the machine."
        ),
    )
    api_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text=_("API Key for authenticated when the machine accesses the API."),
    )
    chip = models.CharField(
        max_length=100, default=SupportedChips.ESP32, choices=SupportedChips.choices
    )
    firmware_version = models.CharField(max_length=50, null=True, blank=True)

    log_booted = models.BooleanField(default=True, help_text=_("Log boot events"))
    log_enabled = models.BooleanField(
        default=True, help_text=_("Log successful unlock events")
    )
    log_disabled = models.BooleanField(
        default=False, help_text=_("Log when machine is disabled again")
    )
    log_unsuccessful = models.BooleanField(
        default=False, help_text=_("Log unsuccessful unlock attempts")
    )

    runtimer = models.DurationField(
        default=timedelta(),
        help_text=_("Time until the machine is locked again when it is not active."),
    )
    min_power = models.IntegerField(
        default=10,
        help_text=_(
            "Minimum power consumption in watts for the machine to be considered active."
        ),
    )
    control_parameter = models.CharField(max_length=100, null=True, blank=True)
    display_time_countdown = models.BooleanField(
        default=True,
        help_text=_(
            "Whether the machine displays the time remaining until it locks again when it is unlocked but not active."
        ),
    )
    display_power_consumption = models.BooleanField(
        default=True,
        help_text=_("If the machine displays the power consumption when it is active."),
    )
    link_relays = models.BooleanField(
        default=False,
        help_text=_(
            "If set, the machine relays are linked and the secondary relay is activated together with the primary relay."
        ),
    )

    access_control_module = models.IntegerField(
        default=0, choices=ACCESS_CONTROL_MODULES
    )
    access_control_module_settings = models.JSONField(default=dict, blank=True)
    status_display_module = models.IntegerField(
        default=0, choices=STATUS_DISPLAY_MODULES
    )
    status_display_module_settings = models.JSONField(default=dict, blank=True)
    actor_module = models.IntegerField(default=0, choices=ACTOR_MODULES)
    actor_module_settings = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Machine")
        verbose_name_plural = _("Machines")
        ordering = ["name"]
        permissions = (("view_machine_state", _("View Machine State")),
                       ("view_machine_logs", _("View Machine Logs")),
                       ("send_machine_commands", _("Send Machine Commands")))

    def __str__(self):
        return self.name

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
        if not times.all():
            return datetime.time(23, 59, 59)
        now = datetime.datetime.now()
        try:
            return (
                times.filter(weekdays__contains=now.weekday())
                .filter(start_time__lte=now.time())
                .filter(end_time__gte=now.time())
                .first()
                .end_time
            )
        except AttributeError:
            return None
        except MachineTime.DoesNotExist:
            return None

    @staticmethod
    def get_valid_end_time_for_machine(machine_id):
        query = MachineTime.objects.filter(machine_id=machine_id)
        return Machine.get_valid_end_time_for_times(query)

    def get_valid_end_time(self):
        return Machine.get_valid_end_time_for_times(self.times)


class MachineTime(TimestampedModel):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="times")
    weekdays = WeekdayField()
    start_time = models.TimeField()
    end_time = models.TimeField()


class MachineRegistrationRequest(TimestampedModel):
    mac_address = models.CharField(max_length=17, db_index=True)
    hostname = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()

    class Meta:
        verbose_name = _("Registration Request")
        verbose_name_plural = _("Registration Requests")
        ordering = ["-created"]

    def __str__(self):
        return self.mac_address
    

class MachineControlKey(TimestampedModel):
    machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="control_keys"
    )
    key = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purpose = models.CharField(max_length=100)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Control Key")
        verbose_name_plural = _("Control Keys")
        ordering = ["-created"]

    def __str__(self):
        return self.purpose

class MachineConnection(TimestampedModel):
    primary_machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="as_primary_machine"
    )
    secondary_machine = models.ForeignKey(
        Machine, on_delete=models.CASCADE, related_name="as_secondary_machine"
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