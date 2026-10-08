from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Person, Qualification, PERMISSION_LEVELS
from .conf import PERSON_ENABLE_SLACK_EMAIL, PERSON_ENABLE_EMAIL

def make_person_fields():
    fields = ["member_id", "name", "language", "notes", "is_active"]
    if PERSON_ENABLE_SLACK_EMAIL:
        fields.insert(1, "slack_email")
    if PERSON_ENABLE_EMAIL:
        fields.insert(1, "email")
    return fields
class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = make_person_fields()


class InstructorFieldsMixin:
    """Only users with `people.change_instructor` may appoint instructors and maintainers.

    Without it the fields are disabled, so submitted values are ignored and the
    stored (or default) value is kept.
    """

    instructor_fields = ("is_instructor", "is_maintainer")

    def restrict_instructor_fields(self, user):
        if user is None or not user.has_perm("people.change_instructor"):
            for field_name in self.instructor_fields:
                self.fields[field_name].disabled = True


class QualifyPersonForm(InstructorFieldsMixin, forms.ModelForm):
    class Meta:
        model = Qualification
        fields = [
            "machine",
            "person",
            "instructed_by",
            "permission_level",
            "is_instructor",
            "is_maintainer",
            "comment",
            "last_used",
            "expires_at",
            "expired",
            "notified_at",
        ]
        widgets = {
            "person": forms.HiddenInput(),
            "machine": forms.HiddenInput(),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }

    read_only_expiration_fields = ("last_used", "expires_at", "expired")
    editable_expiration_fields = ("notified_at",)

    def __init__(self, *args, user=None, **kwargs):
        super(QualifyPersonForm, self).__init__(*args, **kwargs)
        self.restrict_instructor_fields(user)

        if self.instance.pk:
            # An existing qualification can't be moved to another person or
            # machine - disabled fields ignore submitted values.
            self.fields["person"].disabled = True
            self.fields["machine"].disabled = True

            instructors = list(
                self.instance.machine.instructors.select_related("person")
                .order_by("person__name")
                .values_list("person__pk", "person__name")
                .all()
            )
            # Keep the stored instructor selectable even if they are no longer
            # an instructor, otherwise saving would silently clear it.
            instructed_by = self.instance.instructed_by
            if instructed_by is not None and instructed_by.pk not in (
                pk for pk, _name in instructors
            ):
                instructors.append((instructed_by.pk, instructed_by.name))
            instructors.insert(0, ("", "---------"))
            self.fields["instructed_by"].choices = instructors
            self.fields["instructed_by"].widget.choices = instructors
            for field_name in self.read_only_expiration_fields:
                self.fields[field_name].disabled = True
        else:
            for field_name in (
                self.read_only_expiration_fields + self.editable_expiration_fields
            ):
                del self.fields[field_name]


class BulkQualifyForm(InstructorFieldsMixin, forms.Form):
    instructed_by = forms.ModelChoiceField(
        label=_("Instructed By"),
        queryset=Person.objects.filter(is_active=True),
        required=False,
    )
    permission_level = forms.ChoiceField(
        label=_("Permission Level"), choices=PERMISSION_LEVELS
    )
    is_instructor = forms.BooleanField(label=_("Is Instructor"), required=False)
    is_maintainer = forms.BooleanField(label=_("Is Maintainer"), required=False)
    comment = forms.CharField(
        label=_("Comment"), required=False, widget=forms.Textarea(attrs={"rows": 4})
    )

    def __init__(self, *args, machine=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.restrict_instructor_fields(user)
        if machine is not None:
            self.fields["instructed_by"].queryset = Person.objects.filter(
                qualifications__machine=machine, qualifications__is_instructor=True
            ).order_by("name")
