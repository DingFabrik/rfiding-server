from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.core.paginator import Paginator
from django.views.generic import (
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.views import BaseToggleActiveView, BaseListView, PartialMixin, TitleMixin
from .models import Person, Qualification, Instructor
from .forms import PersonForm, QualifyPersonForm, InstructorForm
from base.filters import PEOPLE_FILTER_CHOICES


PEOPLE_SORT_CHOICES = (
    ("member_id", _("Member ID")),
    ("name", _("Name")),
    ("email", _("E-Email")),
    ("-updated", _("Last Modified")),
    ("-created", _("Created")),
)

PEOPLE_SORT_CHOICES_KEYS = [choice[0] for choice in PEOPLE_SORT_CHOICES]


class PersonListView(BaseListView):
    permission_required = "people.view_person"

    model = Person
    queryset = Person.objects.values(
        "pk", "name", "email", "is_active", "member_id"
    ).all()
    template_name = "person_list.html"
    context_object_name = "people"
    sort_fields = PEOPLE_SORT_CHOICES_KEYS

    def get_queryset(self):
        queryset = super().get_queryset()
        filter = self.request.GET.get("filter", self.request.user.default_people_filter)
        if filter == "all":
            queryset = queryset
        elif filter == "inactive":
            queryset = queryset.filter(is_active=False)
        else:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sort_choices"] = PEOPLE_SORT_CHOICES
        context["filter_choices"] = PEOPLE_FILTER_CHOICES
        context["filter_default"] = self.request.user.default_people_filter
        return context


class PersonDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "people.view_person"

    model = Person
    template_name = "person_detail.html"
    context_object_name = "person"

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("people.change_person")
        context["can_delete"] = self.request.user.has_perm("people.delete_person")
        qualifications = (
            self.object.qualifications.select_related("machine")
            .select_related("instructed_by")
            .all()
        )
        qualifications_paginator = Paginator(
            qualifications, self.request.user.page_length
        )
        context["qualifications"] = qualifications_paginator.get_page(1)
        can_instruct = self.object.can_instruct.select_related("machine").all()
        can_instruct_paginator = Paginator(can_instruct, self.request.user.page_length)
        context["can_instruct"] = can_instruct_paginator.get_page(1)
        return context


class PersonCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    title = _("Create Person")
    permission_required = "people.add_person"

    model = Person
    template_name = "person_form.html"
    form_class = PersonForm


class PersonUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "people.change_person"

    model = Person
    template_name = "person_form.html"
    form_class = PersonForm
    context_object_name = "person"

    def get_title(self):
        return _(f"Edit {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("people.delete_person")
        return context


class PersonDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "people.delete_person"

    model = Person
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("people:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")


class PersonToggleActiveView(BaseToggleActiveView):
    permission_required = "people.change_person"
    model = Person


class QualifyPersonView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "people.qualify_person"

    model = Qualification
    template_name = "qualify_person.html"
    form_class = QualifyPersonForm

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Person.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualify {self.get_object().name}")

    def get_initial(self):
        return {"person": self.kwargs["pk"]}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_object()
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class RevokeQualificationPersonView(
    TitleMixin, PartialMixin, PermissionRequiredMixin, DeleteView
):
    permission_required = "people.qualify_person"

    model = Qualification
    full_base_template = "base_slim.html"
    partial_base_template = "partial_base_modal.html"
    template_name = "revoke_qualification_confirm.html"

    person = None

    def get_person(self):
        if self.person is None:
            self.person = Person.objects.get(pk=self.kwargs["pk"])
        return self.person

    def get_title(self):
        return _(f"Revoke Qualification for {self.get_person().name}")

    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(
            person=self.kwargs["pk"], pk=self.kwargs["qualification"]
        ).first()

    def get_success_url(self):
        if self.request.GET.get("next"):
            return self.request.GET.get("next")
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class EditQualificationPersonView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "people.qualify_person"

    model = Qualification
    form_class = QualifyPersonForm
    template_name = "qualify_person.html"

    person = None

    def get_person(self):
        if self.person is None:
            self.person = Person.objects.get(pk=self.kwargs["pk"])
        return self.person

    def get_title(self):
        return _(f"Edit Qualification for {self.get_person().name}")

    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(
            person=self.kwargs["pk"], pk=self.kwargs["qualification"]
        ).first()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_person()
        context["machine"] = context["form"].instance.machine
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class PersonQualificationsListView(BaseListView):
    permission_required = "people.view_qualification"
    model = Qualification
    template_name = "person_qualifications_list.html"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Person.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualifications for {self.get_object().name}")

    def get_queryset(self):
        queryset = (
            Qualification.objects.filter(person=self.kwargs["pk"])
            .select_related("machine")
            .all()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_object()
        context["qualifications"] = context["page_obj"]
        return context


class AddInstructorPersonView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "people.change_instructors"

    model = Instructor
    template_name = "instructor_person.html"
    form_class = InstructorForm

    person = None

    def get_person(self):
        if self.person is None:
            self.person = Person.objects.get(pk=self.kwargs["pk"])
        return self.person

    def get_title(self):
        return _(f"Make {self.get_person().name} Instructor")

    def get_initial(self):
        return {"person": self.kwargs["pk"]}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_person()
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class RevokeInstructorPersonView(
    TitleMixin, PartialMixin, PermissionRequiredMixin, DeleteView
):
    permission_required = "people.change_instructors"

    model = Instructor
    full_base_template = "base_slim.html"
    partial_base_template = "partial_base_modal.html"
    template_name = "revoke_instructor_confirm.html"

    person = None

    def get_person(self):
        if self.person is None:
            self.person = Person.objects.get(pk=self.kwargs["pk"])
        return self.person

    def get_title(self):
        return _(f"Revoke {self.get_person().name} as Instructor")

    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(
            person=self.kwargs["pk"], pk=self.kwargs["instructor"]
        ).first()

    def get_success_url(self):
        if self.request.GET.get("next"):
            return self.request.GET.get("next")
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class PersonInstructorListView(BaseListView):
    permission_required = "people.view_instructor"
    model = Instructor
    template_name = "person_instructor_list.html"
    context_object_name = "instructors"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Person.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Instuctor {self.get_object().name}")

    def get_queryset(self):
        queryset = (
            Instructor.objects.filter(person=self.kwargs["pk"])
            .select_related("machine")
            .all()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["person"] = self.get_object()
        context["can_instruct"] = context["page_obj"]
        return context
