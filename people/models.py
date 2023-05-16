from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from machines.models import Machine

class Person(models.Model):
    member_id = models.CharField(max_length=8, verbose_name=_("Member ID"))
    name = models.CharField(max_length=100, verbose_name=_("Full Name"))
    email = models.CharField(max_length=100, blank=True, verbose_name=_("E-Mail"))
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("people:detail", kwargs={"pk": self.pk})
    
class Qualification(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="qualified_people")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="qualifications")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)