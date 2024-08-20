from django import forms

from .models import Token

class TokenForm(forms.ModelForm):
    class Meta:
        model = Token
        fields = ['serial', 'person', 'purpose', 'is_active']