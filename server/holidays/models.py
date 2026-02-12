from django.db import models
from django.utils.translation import gettext as _

class Holiday(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)
    repeats_annually = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["date"]
        
    cache = {
        "date": None,
        "holiday": None
    }

    def __str__(self):
        return f"{self.name} on {self.date}"
    
    def save(self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,):
        Holiday.cache["date"] = None
        Holiday.cache["holiday"] = None
        return super().save(force_insert=force_insert,
                            force_update=force_update,
                            using=using,
                            update_fields=update_fields)