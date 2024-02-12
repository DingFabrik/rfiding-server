from django import forms

from . import utils
from .models import Machine

class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ['name', 'hostname', 'ip_address', 'mac_address', 'is_active']