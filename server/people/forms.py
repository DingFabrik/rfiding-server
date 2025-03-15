from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Person, Qualification, Instructor


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["member_id", "name", "email", "is_active", "notes"]


class QualifyPersonForm(forms.ModelForm):
    machine_autocomplete = forms.CharField(label=_("Machine"), required=False)
    person_autocomplete = forms.CharField(label=_("Person"), required=False)

    class Meta:
        model = Qualification
        fields = ["machine", "person", "instructed_by", "permission_level", "comment"]
        widgets = {
            "person": forms.HiddenInput(),
            "machine": forms.HiddenInput(),
            "machine_autocomplete": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Machine name or hostname"),
                }
            ),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super(QualifyPersonForm, self).__init__(*args, **kwargs)

        if self.instance.pk:
            instructors = list(
                self.instance.machine.instructors.select_related("person")
                .order_by("person__name")
                .values_list("person__pk", "person__name")
                .all()
            )
            instructors.insert(0, ("", "---------"))
            self.fields["instructed_by"].choices = instructors
            self.fields["instructed_by"].widget.choices = instructors


class InstructorForm(forms.ModelForm):
    machine_autocomplete = forms.CharField(label=_("Machine"), required=False)
    person_autocomplete = forms.CharField(label=_("Person"), required=False)

    class Meta:
        model = Instructor
        fields = ["machine", "person"]
        widgets = {
            "person": forms.HiddenInput(),
            "machine": forms.HiddenInput(),
            "machine_autocomplete": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Machine name or hostname"),
                }
            ),
        }
