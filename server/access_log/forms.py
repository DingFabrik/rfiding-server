from django import forms
from django.utils.translation import gettext_lazy as _

from .models import LOG_TYPES

class AccessLogFilterForm(forms.Form):
    action = forms.ChoiceField(
        choices=[("all", _("All"))] + [(x[0], x[1]) for x in LOG_TYPES],
        required=False,
    )