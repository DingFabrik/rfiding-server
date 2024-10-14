from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.views import BaseToggleActiveView, PartialListMixin
from .models import Person, Qualification, Instructor
from .forms import PersonForm, QualifyPersonForm, InstructorForm


PEOPLE_SORT_CHOICES = (
    ("pk", _("Default")),
    ("name", _("Name")),
    ("email", _("E-Email")),
    ("member_id", _("Member ID")),
    ("-updated", _("Last Modified")),
)

PEOPLE_SORT_CHOICES_KEYS = [choice[0] for choice in PEOPLE_SORT_CHOICES]
class PersonListView(PartialListMixin, ListView, PermissionRequiredMixin):
    permission_required = "people.view_person"
    model = Person
    queryset = Person.objects.values(
        "pk", "name", "email", "is_active", "member_id"
    ).all()
    template_name = "person_list.html"
    context_object_name = "people"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        sort = self.request.GET.get("sort")
        if sort in PEOPLE_SORT_CHOICES_KEYS:
            queryset = queryset.order_by(sort)
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("people.create_person")
        context["model"] = self.model
        context["sort_choices"] = PEOPLE_SORT_CHOICES
        return context


class PersonDetailView(DetailView, PermissionRequiredMixin):
    permission_required = "people.view_person"

    model = Person
    template_name = "person_detail.html"
    context_object_name = "person"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("people.change_person")
        context["can_delete"] = self.request.user.has_perm("people.delete_person")
        context["qualifications"] = (
            self.object.qualifications.select_related("machine")
            .select_related("instructed_by")
            .all()
        )
        context["can_instruct"] = self.object.can_instruct.select_related(
            "machine"
        ).all()
        return context


class PersonCreateView(CreateView, PermissionRequiredMixin):
    permission_required = "people.add_person"

    model = Person
    template_name = "person_form.html"
    form_class = PersonForm
    success_url = reverse_lazy("people:list")


class PersonUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = "people.change_person"

    model = Person
    template_name = "person_form.html"
    form_class = PersonForm
    context_object_name = "person"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("people.delete_person")
        return context


class PersonDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = "people.delete_person"

    model = Person
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("people:list")


class PersonToggleActiveView(BaseToggleActiveView):
    permission_required = "people.change_person"
    model = Person


class QualifyPersonView(CreateView, PermissionRequiredMixin):
    permission_required = "people.qualify_person"

    model = Qualification
    template_name = "qualify_person.html"
    form_class = QualifyPersonForm

    def get_initial(self):
        return {"person": self.kwargs["pk"]}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = Person.objects.get(pk=self.kwargs["pk"])
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class RevokeQualificationPersonView(DeleteView, PermissionRequiredMixin):
    permission_required = "people.qualify_person"

    model = Qualification
    template_name = "revoke_qualification_confirm.html"

    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(
            person=self.kwargs["pk"], pk=self.kwargs["qualification"]
        ).first()

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class EditQualificationPersonView(UpdateView, PermissionRequiredMixin):
    permission_required = "people.qualify_person"

    model = Qualification
    form_class = QualifyPersonForm
    template_name = "qualify_person.html"

    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(
            person=self.kwargs["pk"], pk=self.kwargs["qualification"]
        ).first()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = Person.objects.get(pk=self.kwargs["pk"])
        context["machine"] = context["form"].instance.machine
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class AddInstructorPersonView(CreateView, PermissionRequiredMixin):
    permission_required = "people.change_instructors"

    model = Instructor
    template_name = "instructor_person.html"
    form_class = InstructorForm

    def get_initial(self):
        return {"person": self.kwargs["pk"]}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = Person.objects.get(pk=self.kwargs["pk"])
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class RevokeInstructorPersonView(DeleteView, PermissionRequiredMixin):
    permission_required = "people.change_instructors"

    model = Instructor
    template_name = "revoke_instructor_confirm.html"

    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(
            person=self.kwargs["pk"], pk=self.kwargs["instructor"]
        ).first()

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})
