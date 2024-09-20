from django import forms

from .models import RFIDingUser

class UserForm(forms.ModelForm):
    
    class Meta:
        model = RFIDingUser
        fields = ["name", "email", "is_superuser", "is_staff", "is_active", "user_permissions"]
        widgets = {
            "user_permissions": forms.SelectMultiple(attrs={"size":"15"}),
        }