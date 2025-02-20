from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy

from .models import Location
from base.views import TitleMixin, PartialListMixin

class LocationListView(TitleMixin, PartialListMixin, PermissionRequiredMixin, ListView):
    permission_required = "locations.view_location"
    title = _("Locations")
    
    model = Location
    template_name = "location_list.html"
    context_object_name = "locations"
    
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

class LocationDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "locations.view_location"
    title = _("Location")
    
    model = Location
    template_name = "location_detail.html"
    context_object_name = "location"
    
    def get_title(self):
        return self.get_object().name

class LocationCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "locations.add_location"
    title = _("Create Location")
    
    model = Location
    template_name = "location_form.html"
    fields = ["name", "description", "parent"]
    

class LocationUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "locations.change_location"
    title = _("Edit Location")
    
    model = Location
    template_name = "location_form.html"
    fields = ["name", "description", "parent"]
    
    def get_title(self):
        return _("Edit ${self.object.name}")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("locations.delete_location")
        return context
    
    
class LocationDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "locations.delete_location"
    title = _("Delete Location")
    
    model = Location
    template_name = "location_confirm_delete.html"
    success_url = reverse_lazy("locations:list")
    
    def get_title(self):
        return _("Delete ${self.object.name}")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("locations.delete_location")
        return context