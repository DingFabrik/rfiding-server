from django.db import models

from people.models import Person

class Token(models.Model):
    serial = models.CharField(max_length=10)
    purpose = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField()

    owner = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="tokens")