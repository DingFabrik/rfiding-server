from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy

from base.views import BaseToggleActiveView
from .models import Person, Qualification, Instructor
from .forms import PersonForm,  QualifyPersonForm, InstructorForm

class PersonListView(ListView, PermissionRequiredMixin):
    permission_required = 'people.view_person'

    model = Person
    template_name = 'person_list.html'
    context_object_name = 'people'

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("people.create_person")
        context["model"] = self.model
        return context

class PersonDetailView(DetailView, PermissionRequiredMixin):
    permission_required = 'people.view_person'

    model = Person
    template_name = 'person_detail.html'
    context_object_name = 'person'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.request.user.has_perm('people.change_person')
        context['can_delete'] = self.request.user.has_perm('people.delete_person')
        context['qualifications'] = self.object.qualifications.select_related('machine').select_related('instructed_by').all()
        context['can_instruct'] = self.object.can_instruct.select_related('machine').all()
        return context

class PersonCreateView(CreateView, PermissionRequiredMixin):
    permission_required = 'people.add_person'

    model = Person
    template_name = 'person_form.html'
    form_class = PersonForm
    success_url = reverse_lazy('people:list')

class PersonUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = 'people.change_person'

    model = Person
    template_name = 'person_form.html'
    form_class = PersonForm
    context_object_name = 'person'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete'] = self.request.user.has_perm('people.delete_person')
        return context

class PersonDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = 'people.delete_person'
    
    model = Person
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('people:list')

class PersonToggleActiveView(BaseToggleActiveView):
    permission_required = 'people.change_person'
    model = Person

class QualifyPersonView(CreateView, PermissionRequiredMixin):
    permission_required = 'people.qualify_person'
    
    model = Qualification
    template_name = 'qualify_person.html'
    form_class = QualifyPersonForm

    def get_initial(self):
        return {
            'person': self.kwargs['pk']
        }
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.kwargs['pk'])
        return context

    def get_success_url(self):
        return reverse_lazy('people:detail', kwargs={'pk': self.kwargs['pk']})
    
class RevokeQualificationPersonView(DeleteView, PermissionRequiredMixin):
    permission_required = 'people.qualify_person'
    
    model = Qualification
    template_name = 'delete_confirm.html'
    
    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(person=self.kwargs['pk'], pk=self.kwargs['qualification']).first()
    

    def get_success_url(self):
        return reverse_lazy('people:detail', kwargs={'pk': self.kwargs['pk']})
    
class AddInstructorPersonView(CreateView, PermissionRequiredMixin):
    permission_required = 'people.change_instructors'
    
    model = Instructor
    template_name = 'instructor_person.html'
    form_class = InstructorForm

    def get_initial(self):
        return {
            'person': self.kwargs['pk']
        }
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.kwargs['pk'])
        return context

    def get_success_url(self):
        return reverse_lazy('people:detail', kwargs={'pk': self.kwargs['pk']})
    
class RevokeInstructorPersonView(DeleteView, PermissionRequiredMixin):
    permission_required = 'people.change_instructors'
    
    model = Instructor
    template_name = 'delete_confirm.html'
    
    def get_object(self, queryset: QuerySet[Any] | None = ...) -> Model:
        return self.model.objects.filter(person=self.kwargs['pk'], pk=self.kwargs['instructor']).first()
    

    def get_success_url(self):
        return reverse_lazy('people:detail', kwargs={'pk': self.kwargs['pk']})