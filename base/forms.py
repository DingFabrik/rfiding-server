from django import forms
from django.utils.translation import gettext_lazy as _

class InitialSetupForm(forms.Form):
    admin_username = forms.CharField(max_length=200)
    admin_password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
