from django import forms

from .utils import DAY_CHOICES
from .models import Machine, MachineTime


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ["name", "hostname", "ip_address", "mac_address", "is_active", "needs_qualification", "completed_setup", "chip"]


class ConfigureMachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ["runtimer", "min_power", "control_parameter"]


class ConfigureMachineTimeForm(forms.ModelForm):
    weekdays = forms.MultipleChoiceField(
        choices=DAY_CHOICES, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = MachineTime
        fields = ["weekdays", "start_time", "end_time"]


MachineTimeFormset = forms.modelformset_factory(
    MachineTime, extra=3, max_num=7, form=ConfigureMachineTimeForm
)
