from django.views.generic import TemplateView, ListView
import platform
import django
from django.contrib.auth.mixins import PermissionRequiredMixin
from auditlog.models import LogEntry

from rfiding import settings


class AboutView(TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["version"] = settings.VERSION
        context["python_version"] = platform.python_version()
        context["django_version"] = django.get_version()
        return context


class BaseToggleActiveView(TemplateView, PermissionRequiredMixin):
    template_name = "snippets/active_toggle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        object = self.model.objects.get(pk=self.kwargs["pk"])
        object.is_active = not object.is_active
        object.save()
        context["object"] = object
        return context

class PartialMixin:
    full_base_template = "base.html"
    partial_base_template = "partial_base.html"
    
    @property
    def is_partial(self):
        return self.request.headers.get("HX-Request") == "true"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_template"] = self.partial_base_template if self.is_partial else self.full_base_template
        context["is_partial"] = self.is_partial
        return context

class PartialListMixin(PartialMixin):
    full_base_template = "base_list.html"
    partial_base_template = "partial_base_list.html"
    
class AuditlogView(PartialListMixin, ListView, PermissionRequiredMixin):
    model = LogEntry
    queryset = LogEntry.objects.all().select_related("content_type").order_by("-timestamp")
    permission_required = "tokens.view_token"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if "search" in self.request.GET:
            queryset = queryset.filter(
                object_repr__icontains=self.request.GET["search"]
            )
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        return context