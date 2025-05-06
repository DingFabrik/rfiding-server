from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML
from crispy_forms.bootstrap import AppendedText, FormActions
from django.utils.translation import gettext as _

from .utils import DAY_CHOICES
from .models import Machine, MachineTime


class MachineForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "name",
            "type",
            "parent",
            "location",
            "is_active",
            "needs_qualification",
            Fieldset(
                _("Network"),
                "hostname",
                "ip_address",
                "mac_address",
                css_class="border rounded p-2 mb-3",
                css_id="network-fieldset",
            ),
            Fieldset(
                _("Logging"),
                "log_booted",
                "log_enabled",
                "log_disabled",
                "log_unsuccessful",
                css_class="border rounded p-2 mb-3",
                css_id="logging-fieldset",
            ),
            Fieldset(
                _("Security"),
                "encryption_key",
                "api_key",
                css_class="border rounded p-2 mb-3",
                css_id="security-fieldset",
            ),
            Fieldset(_("Client"),
                     "chip",
                     css_class="border rounded p-2 mb-3",
                     css_id="client-fieldset",
                     ),
            FormActions(
                Submit("submit", _("Save")),
                HTML(
                    """{% load i18n %}{% if object and can_delete %}
            <a class="btn btn-danger float-end" href="{% url request.resolver_match.namespace|add:':delete' object.pk %}">
                <i class="bi-trash me-1"></i> {% trans 'Delete' %}
            </a>
        {% endif %}"""
                ),
            ),
        )

    class Meta:
        model = Machine
        fields = [
            "name",
            "type",
            "parent",
            "hostname",
            "ip_address",
            "mac_address",
            "location",
            "is_active",
            "needs_qualification",
            "chip",
            "encryption_key",
            "api_key",
            "log_booted",
            "log_enabled",
            "log_disabled",
            "log_unsuccessful",
        ]
        widgets = {
            "encryption_key": forms.PasswordInput(render_value=True),
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
