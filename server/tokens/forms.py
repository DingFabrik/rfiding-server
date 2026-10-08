from django import forms

from .models import Token


class TokenForm(forms.ModelForm):
    class Meta:
        model = Token
        fields = ["serial", "person", "is_active", "type", "label_id", "notes"]

        widgets = {
            "person": forms.HiddenInput(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
