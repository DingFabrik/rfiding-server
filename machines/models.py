import datetime
from django.db import models
from base.models import TimestampedModel
from django.utils.translation import gettext as _
from django.urls import reverse

from machines.fields import WeekdayFormField

def is_str(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)

class WeekdayField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 20
        super(WeekdayField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        return super(WeekdayField, self).formfield(form_class=WeekdayFormField, **kwargs)

    def to_python(self, value):
        if is_str(value):
            if value:
                value = [int(x) for x in value.strip('[]').split(',') if x]
            else:
                value = []
        return value

    def get_db_prep_value(self, value, connection=None, prepared=False):
        return ",".join([str(x) for x in value or []])

class Machine(TimestampedModel):
    name = models.CharField(max_length=100)
    mac_address = models.CharField(max_length=17)
    hostname = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Machine")
        verbose_name_plural = _("Machines")
        ordering = ["pk"]

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("machines:detail", kwargs={"pk": self.pk})
    
    def is_now_valid_time(self):
        if not self.times.all():
            return True
        return self.times.filter(weekdays__contains=[datetime.datetime.today().weekday()]).filter(start_time__lte=datetime.datetime.now().time()).filter(end_time__gte=datetime.datetime.now().time()).exists()

class MachineConfig(TimestampedModel):
    machine = models.OneToOneField(Machine, on_delete=models.CASCADE, related_name='config')
    runtimer = models.IntegerField(default=0)
    min_power = models.IntegerField(default=0)
    control_parameter = models.CharField(max_length=100)

class MachineTimes(TimestampedModel):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='times')
    weekdays = WeekdayField()
    start_time = models.TimeField()
    end_time = models.TimeField()