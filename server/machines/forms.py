from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import AppendedText

from .utils import DAY_CHOICES
from .models import Machine, MachineTime


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = [
            "name",
            "hostname",
            "ip_address",
            "mac_address",
            "location",
            "is_active",
            "needs_qualification",
            "chip",
            "encryption_key"
        ]
        widgets = {
            "encryption_key": forms.PasswordInput(),
        }


class ConfigureMachineForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            AppendedText("runtimer", "h:m:s"),
            AppendedText("min_power", "w"),
            "display_time_countdown",
            "display_power_consumption",
            "link_relays",
        )
    class Meta:
        model = Machine
        fields = [
            "runtimer",
            "min_power",
            "display_time_countdown",
            "display_power_consumption",
            "link_relays",
        ]


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
