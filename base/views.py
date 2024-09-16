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

class AuditlogView(ListView):
    model = LogEntry
    queryset = LogEntry.objects.all().order_by("-timestamp")
    permission_required = "tokens.view_token"

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        return context
