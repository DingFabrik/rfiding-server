from django import forms
from django.contrib.auth.models import Group

from .models import RFIDingUser

class UserForm(forms.ModelForm):
    
    class Meta:
        model = RFIDingUser
        fields = ["name", "email", "is_superuser", "is_active", "groups", "user_permissions"]
        widgets = {
            "user_permissions": forms.SelectMultiple(attrs={"size":"17"}),
        }
        
class GroupForm(forms.ModelForm):
    
    class Meta:
        model = Group
        fields = ["name", "permissions"]
        widgets = {
            "permissions": forms.SelectMultiple(attrs={"size":"17"}),
        }