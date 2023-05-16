from django.db import models

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


class MachineTimes(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    
    start_time = models.TimeField()
    end_time = models.TimeField()