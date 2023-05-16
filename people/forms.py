from django.forms import ModelForm

from people.models import Person

class PersonForm(ModelForm):
    class Meta:
        model = Person
        fields = ["member_id", "name", "email", "is_active"]