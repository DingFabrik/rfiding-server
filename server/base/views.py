from django.views.generic import TemplateView, ListView
import platform
import django
from django.contrib.auth.mixins import PermissionRequiredMixin
from auditlog.models import LogEntry
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.cache import get_cache_key

from rfiding import settings
from machines.models import Machine
from people.models import Person
from tokens.models import Token
class PartialMixin:
    full_base_template = "base.html"
    partial_base_template = "partial_base.html"

    @property
    def is_partial(self):
        return self.request.headers.get("HX-Request") == "true"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_template"] = (
            self.partial_base_template if self.is_partial else self.full_base_template
        )
        context["is_partial"] = self.is_partial
        return context


class PartialListMixin(PartialMixin):
    full_base_template = "base_list.html"
    partial_base_template = "partial_base_list.html"


class TitleMixin:
    title = None

    def get_title(self):
        return self.title

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["html_title"] = self.get_title()
        return context


class AboutView(TitleMixin, TemplateView):
    title = _("About")
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["version"] = settings.VERSION
        context["python_version"] = platform.python_version()
        context["django_version"] = django.get_version()
        return context


class BaseListView(PartialListMixin, TitleMixin, PermissionRequiredMixin, ListView):
    search_field = "name"
    sort_fields = []

    def get_title(self):
        return self.model._meta.verbose_name_plural

    def sort_queryset(self, queryset):
        sort = self.request.GET.get("sort")
        if sort in self.sort_fields:
            return queryset.order_by(sort)
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        if "search" in self.request.GET:
            queryset = queryset.filter(
                **{f"{self.search_field}__icontains": self.request.GET["search"]}
            )
        return self.sort_queryset(queryset)

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["can_create"] = self.request.user.has_perm(
            f"{self.model._meta.app_label}.add_{self.model._meta.model_name}"
        )
        context["can_edit"] = self.request.user.has_perm(
            f"{self.model._meta.app_label}.change_{self.model._meta.model_name}"
        )
        context["model_count"] = self.get_queryset().count()
        return context


class BaseToggleActiveView(PermissionRequiredMixin, TemplateView):
    template_name = "snippets/active_toggle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        object = self.model.objects.get(pk=self.kwargs["pk"])
        object.is_active = not object.is_active
        object.save()
        context["object"] = object
        return context


class AuditlogView(TitleMixin, PartialListMixin, PermissionRequiredMixin, ListView):
    title = _("Audit Log")
    model = LogEntry
    queryset = (
        LogEntry.objects.all().select_related("content_type").order_by("-timestamp")
    )
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


def expire_page(path):
    request = HttpRequest()
    request.path = path
    key = get_cache_key(request)
    if cache.has_key(key):
        cache.delete(key)

class UniversalSearchView(TitleMixin, TemplateView):
    title = _("Search")
    template_name = "search_universal_results.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        m = Machine.objects.filter(name__icontains=self.request.GET["search"])[:10]
        p = Person.objects.filter(name__icontains=self.request.GET["search"])[:10]
        t = Token.objects.filter(serial__icontains=self.request.GET["search"])[:10]
        context["objects"] = list(m) + list(p) + list(t)
        return context