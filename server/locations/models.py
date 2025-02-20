from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.models import TimestampedModel

class Location(TimestampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("locations:detail", kwargs={"pk": self.pk})