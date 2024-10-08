from typing import Any
from django.db.models.query import QuerySet
from django.views.generic import ListView

from base.views import PartialListMixin
from .models import AccessLog
from .forms import AccessLogFilterForm
from tokens.models import Token
from machines.models import Machine
from people.models import Person

class AccessLogListView(PartialListMixin, ListView):
    model = AccessLog
    queryset = AccessLog.objects.select_related("token").select_related("machine").all()
    template_name = "access_log_list.html"
    context_object_name = "access_logs"
    ordering = ["-timestamp"]
    
    def get_queryset(self) -> QuerySet[Any]:
        queryset =  super().get_queryset()
        if "action" in self.request.GET and self.request.GET["action"] != "all":
            queryset = queryset.filter(type=self.request.GET["action"])
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm(
            "access_log.create_accesslog"
        )
        context["filter_form"] = AccessLogFilterForm(self.request.GET)
        context["model"] = self.model
        return context


class AccessLogForTokenView(PartialListMixin, ListView):
    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]
    template_name = "access_log_for_token.html"

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(token__pk=self.kwargs["token"])

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["token"] = Token.objects.get(pk=self.kwargs["token"])
        return context

class AccessLogForPersonView(PartialListMixin, ListView):
    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]
    template_name = "access_log_for_person.html"

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().select_related("machine").filter(token__person__pk=self.kwargs["person"])

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["person"] = Person.objects.get(pk=self.kwargs["person"])
        return context


class AccessLogForMachineView(PartialListMixin, ListView):
    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]
    template_name = "access_log_for_machine.html"

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(machine__pk=self.kwargs["machine"])

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["machine"] = Machine.objects.get(pk=self.kwargs["machine"])
        return context
