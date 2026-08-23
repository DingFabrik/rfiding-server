from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.query import QuerySet
from django.views.generic import ListView
from django.utils.translation import gettext_lazy as _

from base.views import PartialListMixin, TitleMixin
from .models import AccessLog, LOG_TYPES
from tokens.models import Token
from machines.models import Machine
from people.models import Person


class AccessLogListView(TitleMixin, PermissionRequiredMixin, PartialListMixin, ListView):
    permission_required = "access_log.view_accesslog"

    title = _("Access Logs")
    model = AccessLog
    queryset = AccessLog.objects.select_related("token").select_related("machine").all()
    template_name = "access_log_list.html"
    context_object_name = "access_logs"
    ordering = ["-timestamp"]

    def get_queryset(self) -> QuerySet[Any]:
        queryset = super().get_queryset()
        action = self.request.GET.get("filter_action", "all")
        if action != "all":
            queryset = queryset.filter(type=action)
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = False
        context["filter_choices"] = {
            "action": {
                "label": _("Action"),
                "options": [("all", _("All"))] + list(LOG_TYPES),
            }
        }
        context["filter_default"] = "all"
        context["model_count"] = self.get_queryset().count()
        context["model"] = self.model
        return context


class AccessLogForSubjectView(TitleMixin, PermissionRequiredMixin, PartialListMixin, ListView):
    """Base for the "access log for one token/person/machine" pages.

    Subclasses only need to set subject_type, get_queryset() and
    get_subject(), everything else (title, template, empty state, "go to X"
    link) is derived from that.
    """

    permission_required = "access_log.view_accesslog"

    model = AccessLog
    context_object_name = "access_logs"
    ordering = ["-timestamp"]
    template_name = "access_log_for_subject.html"
    subject_type = None
    subject_labels = {
        "token": _("token"),
        "person": _("person"),
        "machine": _("machine"),
    }
    empty_messages = {
        "token": _("This token has not been used yet."),
        "person": _("This person has not accessed anything yet."),
        "machine": _("This machine has not been used yet."),
    }

    def get_subject(self):
        raise NotImplementedError

    def get_cached_subject(self):
        if not hasattr(self, "_subject"):
            self._subject = self.get_subject()
        return self._subject

    def get_title(self):
        return _("Access Log for %(subject)s") % {"subject": self.get_cached_subject()}

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.get_cached_subject()
        context["model"] = self.model
        context["subject_type"] = self.subject_type
        context["subject"] = subject
        context["subject_url"] = subject.get_absolute_url()
        context["subject_action_label"] = _("Go to %(subject_type)s") % {
            "subject_type": self.subject_labels[self.subject_type]
        }
        context["empty_message"] = self.empty_messages[self.subject_type]
        return context


class AccessLogForTokenView(AccessLogForSubjectView):
    subject_type = "token"

    def get_queryset(self) -> QuerySet[Any]:
        return (
            super()
            .get_queryset()
            .select_related("machine")
            .filter(token__pk=self.kwargs["token"])
        )

    def get_subject(self):
        return Token.objects.get(pk=self.kwargs["token"])


class AccessLogForPersonView(AccessLogForSubjectView):
    subject_type = "person"

    def get_queryset(self) -> QuerySet[Any]:
        return (
            super()
            .get_queryset()
            .select_related("machine", "token")
            .filter(token__person__pk=self.kwargs["person"])
        )

    def get_subject(self):
        return Person.objects.get(pk=self.kwargs["person"])


class AccessLogForMachineView(AccessLogForSubjectView):
    subject_type = "machine"

    def get_queryset(self) -> QuerySet[Any]:
        return (
            super()
            .get_queryset()
            .select_related("token")
            .filter(machine__pk=self.kwargs["machine"])
        )

    def get_subject(self):
        return Machine.objects.get(pk=self.kwargs["machine"])
