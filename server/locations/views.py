from django.views.generic import (
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy

from .models import Location
from base.views import TitleMixin, BaseListView


class LocationListView(BaseListView):
    permission_required = "locations.view_location"

    model = Location
    template_name = "location_list.html"
    context_object_name = "locations"


class LocationDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "locations.view_location"
    title = _("Location")

    model = Location
    template_name = "location_detail.html"
    context_object_name = "location"

    def get_title(self):
        return self.get_object().name
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("locations.change_location")
        context["can_delete"] = self.request.user.has_perm("locations.delete_location")
        return context


class LocationCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "locations.add_location"
    title = _("Create Location")

    model = Location
    template_name = "base_form.html"
    fields = ["name", "description", "parent"]


class LocationUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "locations.change_location"
    title = _("Edit Location")

    model = Location
    template_name = "base_form.html"
    fields = ["name", "description", "parent"]

    def get_title(self):
        return _(f"Edit {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("locations.delete_location")
        return context


class LocationDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "locations.delete_location"
    title = _("Delete Location")

    model = Location
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("locations:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("locations.delete_location")
        return context
