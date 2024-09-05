from django import forms
from dal import autocomplete
from django.utils.translation import gettext_lazy as _

from .models import Person, Qualification, Instructor

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['member_id', 'name', 'email', 'is_active', 'notes']

class QualifyPersonForm(forms.ModelForm):
    machine_autocomplete = forms.CharField(label=_('Machine'), required=False)
    class Meta:
        model = Qualification
        fields = ['machine', 'person', 'instructed_by', 'permission_level', 'comment']
        widgets = {
            'person': forms.HiddenInput(),
            'machine': forms.HiddenInput(),
            'machine_autocomplete': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Machine name or hostname'}),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class InstructorForm(forms.ModelForm):
    machine_autocomplete = forms.CharField(label=_('Machine'))
    class Meta:
        model = Instructor
        fields = ['machine', 'person']
        widgets = {
            'person': forms.HiddenInput(),
            'machine': forms.HiddenInput(),
            'machine_autocomplete': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Machine name or hostname'}),
        }