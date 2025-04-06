from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Token


class TokenForm(forms.ModelForm):
    person_autocomplete = forms.CharField(label=_("Person"), required=False)
    class Meta:
        model = Token
        fields = ["serial", "person", "person_autocomplete", "is_active", "type", "label_id", "notes"]

        widgets = {
            "person": forms.HiddenInput(),
            "Person_autocomplete": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Person"),
                }
            ),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }