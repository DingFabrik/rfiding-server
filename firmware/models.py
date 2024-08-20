from django.db import models
from base.models import TimestampedModel

class Firmware(TimestampedModel):
    name = models.CharField("Name", max_length=255)
    version = models.CharField("Version", max_length=255)
    file = models.FileField("File", upload_to='firmware/')
    
    class Meta:
        verbose_name = "Firmware"
        verbose_name_plural = "Firmwares"
    
    def __str__(self):
        return self.name