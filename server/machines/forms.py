from django import forms
from django.utils.translation import gettext_lazy as _

from .utils import DAY_CHOICES
from .models import Machine, MachineTime


class MachineForm(forms.ModelForm):
    # Fields grouped by the settings section (sidebar tab) they are shown in.
    SECTIONS = (
        ("general", _("General"), "info",
         ["name", "type", "parent", "compartment_id", "location", "state"]),
        ("access", _("Access"), "shield-check",
         ["needs_qualification", "permission_level",
          "qualification_expiry_unused_days", "qualification_expiry_used_days"]),
        ("schedule", _("Schedule"), "calendar-clock", ["allowed_on_holidays"]),
        ("session", _("Session"), "timer", ["runtimer", "min_power"]),
        ("device", _("Device"), "cpu",
         ["chip", "hostname", "ip_address", "mac_address", "encryption_key", "api_key"]),
        ("logging", _("Logging"), "list",
         ["log_enabled", "log_unsuccessful", "log_disabled", "log_booted"]),
    )

    class Meta:
        model = Machine
        fields = [
            "name",
            "type",
            "parent",
            "compartment_id",
            "hostname",
            "ip_address",
            "mac_address",
            "location",
            "state",
            "needs_qualification",
            "permission_level",
            "chip",
            "encryption_key",
            "api_key",
            "log_booted",
            "log_enabled",
            "log_disabled",
            "log_unsuccessful",
            "runtimer",
            "min_power",
            "allowed_on_holidays",
            "qualification_expiry_unused_days",
            "qualification_expiry_used_days",
        ]
        widgets = {
            "encryption_key": forms.PasswordInput(render_value=True),
        }


class ConfigureMachineTimeForm(forms.ModelForm):
    weekdays = forms.MultipleChoiceField(
        choices=DAY_CHOICES, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = MachineTime
        fields = ["weekdays", "start_time", "end_time"]


MachineTimeFormset = forms.modelformset_factory(
    MachineTime, extra=0, max_num=7, can_delete=True, form=ConfigureMachineTimeForm
)
