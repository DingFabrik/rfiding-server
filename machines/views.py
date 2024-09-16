from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy

from base.views import BaseToggleActiveView
from .models import Machine
from .forms import MachineForm, ConfigureMachineForm, MachineTimeFormset


class MachineListView(ListView, PermissionRequiredMixin):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_list.html"
    context_object_name = "machines"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("machines.create_machine")
        context["model"] = self.model
        return context


class MachineDetailView(DetailView, PermissionRequiredMixin):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_detail.html"
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("machines.change_machine")
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        if self.object.needs_qualification:
            context["qualifications"] = (
                self.object.qualified_people.select_related("person")
                .select_related("instructed_by")
                .all()
            )
            context["qualifications_count"] = len(context["qualifications"])
            context["instructors"] = self.object.instructors.select_related("person").all()
            context["instructors_count"] = len(context["instructors"])
        return context


class MachineCreateView(CreateView, PermissionRequiredMixin):
    permission_required = "machines.add_machine"

    model = Machine
    template_name = "machine_form.html"
    form_class = MachineForm
    success_url = reverse_lazy("machines:list")


class MachineUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = "machines.change_machine"

    model = Machine
    template_name = "machine_form.html"
    form_class = MachineForm
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        return context


class MachineConfigureView(UpdateView, PermissionRequiredMixin):
    permission_required = "machines.change_machine"

    model = Machine
    template_name = "machine_configure_form.html"
    form_class = ConfigureMachineForm
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formset"] = (
            kwargs["formset"]
            if "formset" in kwargs
            else MachineTimeFormset(
                prefix="times", queryset=context["machine"].times.all()
            )
        )
        return context

    def form_valid(self, form):
        formset = MachineTimeFormset(prefix="times", data=self.request.POST)
        if formset.is_valid():
            self.object = form.save()
            instances = formset.save(commit=False)
            for instance in instances:
                instance.machine = self.object
                instance.save()
            return super().form_valid(form)
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


class MachineDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = "machines.delete_machine"

    model = Machine
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("machines:list")


class MachineToggleActiveView(BaseToggleActiveView):
    permission_required = "machines.change_machine"
    model = Machine
