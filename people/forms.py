from django import forms

from people.models import Person
from machines.models import Machine

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["member_id", "name", "email", "is_active"]