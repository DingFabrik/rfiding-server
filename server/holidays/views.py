from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
)
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy

from .models import Holiday
from base.views import TitleMixin, BaseListView


class HolidayListView(BaseListView):
    permission_required = "holidays.view_holiday"

    model = Holiday
    template_name = "holiday_list.html"
    context_object_name = "holidays"


class HolidayCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "holidays.add_holiday"
    title = _("Create Holiday")

    model = Holiday
    template_name = "base_form.html"
    fields = ["name", "date", "repeats_annually"]
    success_url = reverse_lazy("holidays:list")


class HolidayUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "holidays.change_holiday"
    title = _("Edit Holiday")

    model = Holiday
    template_name = "base_form.html"
    fields = ["name", "date", "repeats_annually"]
    success_url = reverse_lazy("holidays:list")

    def get_title(self):
        return _(f"Edit {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("holidays.delete_holiday")
        return context


class HolidayDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "holidays.delete_holiday"
    title = _("Delete Holiday")

    model = Holiday
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("holidays:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("holidays.delete_holiday")
        return context
