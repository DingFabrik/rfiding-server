import datetime
from django.db import models
from base.models import TimestampedModel
from django.utils.translation import gettext as _
from django.urls import reverse
from auditlog.registry import auditlog

from machines.fields import WeekdayFormField
from .client_modules import ACCESS_CONTROL_MODULES, STATUS_DISPLAY_MODULES, ACTOR_MODULES

SUPPORTED_CHIPS = [
    ("esp32", "ESP32"),
    ("esp8266", "ESP8266"),
    ("esp32s2", "ESP32-S2"),
    ("esp32c3", "ESP32-C3"),
    ("esp32s3", "ESP32-S3"),
]

def is_str(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
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
    name = models.CharField(max_length=100)
    mac_address = models.CharField(max_length=17, db_index=True)
    hostname = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    needs_qualification = models.BooleanField(default=True, help_text=_("If disabled, any active user can access this machine."))
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    encryption_key = models.CharField(max_length=32, null=True, blank=True, help_text=_("32 character encryption key for secure communication with the machine."))
    chip = models.CharField(max_length=100, default=SUPPORTED_CHIPS[0][0], choices=SUPPORTED_CHIPS)
    firmware_version = models.CharField(max_length=50, null=True, blank=True)

    runtimer = models.IntegerField(default=0)
    min_power = models.IntegerField(default=0)
    control_parameter = models.CharField(max_length=100, null=True, blank=True)

    access_control_module = models.IntegerField(default=0, choices=ACCESS_CONTROL_MODULES)
    access_control_module_settings = models.JSONField(default=dict, blank=True)
    status_display_module = models.IntegerField(default=0, choices=STATUS_DISPLAY_MODULES)
    status_display_module_settings = models.JSONField(default=dict, blank=True)
    actor_module = models.IntegerField(default=0, choices=ACTOR_MODULES)
    actor_module_settings = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Machine")
        verbose_name_plural = _("Machines")
        ordering = ["pk"]

    def __str__(self):
        return f"{self.name}"
    
    @property
    def has_api(self):
        return (self.encryption_key is not None and
                len(self.encryption_key) > 0 and
                self.ip_address is not None)

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
    
    def get_valid_end_time(self):
        if not self.times.all():
            return datetime.time(23, 59, 59)
        now = datetime.datetime.now()
        try:
            return (
                self.times.filter(weekdays__contains=now.weekday())
                .filter(start_time__lte=now.time())
                .filter(end_time__gte=now.time())
                .first()
                .end_time
            )
        except AttributeError:
            return None
        except MachineTime.DoesNotExist:
            return None


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
        return f"{self.mac_address}"


auditlog.register(Machine, exclude_fields=["created", "updated"])
auditlog.register(MachineTime, exclude_fields=["created", "updated"])