from django.db import models
from django.urls import reverse

class Machine(models.Model):
    hostname = models.CharField(max_length=200)
    mac_address = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    comment = models.CharField(max_length=2000, blank=True)
    is_active = models.BooleanField(default=True)

    runtimer = models.DurationField(blank=True, null=True)
    min_power = models.IntegerField(blank=True, null=True)
    control_parameter = models.CharField(max_length=200, blank=True)
        
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("machines:detail", kwargs={"pk": self.pk})
    
    def can_be_used(self):
        if not self.is_active:
            return False


class MachineTimes(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    
    start_time = models.TimeField()
    end_time = models.TimeField()

class AccessLogEntry(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True)
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=True)
    was_allowed = models.BooleanField()