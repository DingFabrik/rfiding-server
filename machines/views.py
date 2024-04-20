from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from base.views import BaseToggleActiveView, BaseListView
from .models import Machine
from .forms import MachineForm

class MachineListView(BaseListView, PermissionRequiredMixin):
    permission_required = 'machines.view_machine'

    model = Machine
    template_name = 'machine_list.html'
    context_object_name = 'machines'

    def get_paginate_by(self, queryset):
        return self.request.user.page_length
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("machines.add_machine")
        context["model"] = self.model
        return context


class MachineDetailView(DetailView, PermissionRequiredMixin):
    permission_required = 'machines.view_machine'

    model = Machine
    template_name = 'machine_detail.html'
    context_object_name = 'machine'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.request.user.has_perm('machines.change_machine')
        context['can_delete'] = self.request.user.has_perm('machines.delete_machine')
        context['qualifications'] = self.object.qualified_people.select_related('person').all()
        context['instructors'] = self.object.instructors.select_related('person').all()
        return context
    

class MachineCreateView(CreateView, PermissionRequiredMixin):
    permission_required = 'machines.add_machine'

    model = Machine
    template_name = 'machine_form.html'
    form_class = MachineForm
    success_url = reverse_lazy('machines:list')


class MachineUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = 'machines.change_machine'

    model = Machine
    template_name = 'machine_form.html'
    form_class = MachineForm
    context_object_name = 'machine'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete'] = self.request.user.has_perm('machines.delete_machine')
        return context

class MachineDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = 'machines.delete_machine'

    model = Machine
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('machines:list')

class MachineToggleActiveView(BaseToggleActiveView):
    permission_required = 'machines.change_machine'
    model = Machine