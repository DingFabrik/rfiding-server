from typing import Any
from django.db.models.query import QuerySet
from django.views.generic import ListView

from .models import AccessLog
from tokens.models import Token
from machines.models import Machine
from people.models import Person

class AccessLogListView(ListView):
    model = AccessLog
    queryset = AccessLog.objects.select_related("token").select_related("machine").all()
    template_name = "access_log_list.html"
    context_object_name = "access_logs"
    ordering = ["-timestamp"]

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm(
            "access_log.create_accesslog"
        )
        context["model"] = self.model
        return context


class AccessLogForTokenView(ListView):
    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(token__pk=self.kwargs["token"])

    def get_template_names(self) -> list[str]:
        is_htmx = self.request.headers.get("HX-Request") == "true"
        if is_htmx:
            return ["partial_access_log_for_token.html"]
        else:
            return ["access_log_for_token.html"]

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["token"] = Token.objects.get(pk=self.kwargs["token"])
        context["is_partial"] = self.request.headers.get("HX-Request") == "true"
        return context

class AccessLogForPersonView(ListView):
    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().select_related("machine").filter(token__person__pk=self.kwargs["person"])

    def get_template_names(self) -> list[str]:
        is_htmx = self.request.headers.get("HX-Request") == "true"
        if is_htmx:
            return ["partial_access_log_for_person.html"]
        else:
            return ["access_log_for_person.html"]

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["person"] = Person.objects.get(pk=self.kwargs["person"])
        context["is_partial"] = self.request.headers.get("HX-Request") == "true"
        return context


class AccessLogForMachineView(ListView):
    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(machine__pk=self.kwargs["machine"])

    def get_template_names(self) -> list[str]:
        is_htmx = self.request.headers.get("HX-Request") == "true"
        if is_htmx:
            return ["partial_access_log_for_machine.html"]
        else:
            return ["access_log_for_machine.html"]

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["machine"] = Machine.objects.get(pk=self.kwargs["machine"])
        context["is_partial"] = self.request.headers.get("HX-Request") == "true"
        return context
