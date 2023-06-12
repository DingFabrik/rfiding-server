from django import forms
from machines.models import Machine


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ["hostname", "mac_address", "name", "comment", "is_active"]