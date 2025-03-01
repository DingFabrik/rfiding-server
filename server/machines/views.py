from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import (
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import TruncDay, TruncHour, ExtractWeekDay
from django.db.models import Count
from datetime import datetime, timedelta

from access_log.models import AccessLog, LOG_TYPE_ENABLED
from base.views import BaseToggleActiveView, BaseListView, PartialMixin, TitleMixin
from machines.socket_helper import get_socket_data
from .models import Machine, MachineRegistrationRequest
from .forms import MachineForm, ConfigureMachineForm, MachineTimeFormset
from people.models import Qualification, Instructor
from people.forms import QualifyPersonForm, InstructorForm

MACHINE_SORT_CHOICES = (
    ("name", _("Name")),
    ("hostname", _("Hostname")),
    ("ip_address", _("IP Address")),
    ("mac_address", _("MAC Address")),
    ("-updated", _("Last Modified")),
)
MACHINE_SORT_CHOICES_KEYS = [choice[0] for choice in MACHINE_SORT_CHOICES]

MACHINE_FILTER_CHOICES = (
    ("active", _("Active")),
    ("inactive", _("Inactive")),
    ("all", _("All")),
)


class MachineListView(BaseListView):
    permission_required = "machines.view_machine"
    title = _("Machines")

    model = Machine
    template_name = "machine_list.html"
    context_object_name = "machines"
    sort_fields = MACHINE_SORT_CHOICES_KEYS

    def get_queryset(self):
        queryset = super().get_queryset()
        filter = self.request.GET.get("filter")
        if filter == "all":
            queryset = queryset
        elif filter == "inactive":
            queryset = queryset.filter(is_active=False)
        else:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sort_choices"] = MACHINE_SORT_CHOICES
        context["filter_choices"] = MACHINE_FILTER_CHOICES
        return context


class MachineDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_detail.html"
    context_object_name = "machine"

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("machines.change_machine")
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        try:
            access = AccessLog.objects.filter(machine=self.object).latest("-timestamp")
            context["last_access"] = access.timestamp
        except AccessLog.DoesNotExist:
            context["last_access"] = None
        if self.object.needs_qualification:
            qualifications = (
                self.object.qualified_people.select_related("person")
                .select_related("instructed_by")
                .all()
            )
            qualifications_paginator = Paginator(
                qualifications, self.request.user.page_length
            )
            context["qualifications"] = qualifications_paginator.get_page(1)
            context["qualifications_count"] = qualifications_paginator.count
            instructors = self.object.instructors.select_related("person").all()
            instructors_paginator = Paginator(
                instructors, self.request.user.page_length
            )
            context["instructors"] = instructors_paginator.get_page(1)
            context["instructors_count"] = instructors_paginator.count
        return context


class MachineCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "machines.add_machine"

    def get_title(self):
        return _("Create Machine")

    model = Machine
    template_name = "machine_form.html"
    form_class = MachineForm

    def get_initial(self):
        initial = super().get_initial()
        if "request" in self.request.GET:
            request = MachineRegistrationRequest.objects.get(
                pk=self.request.GET["request"]
            )
            initial["mac_address"] = request.mac_address
            initial["ip_address"] = request.ip_address
            initial["hostname"] = request.hostname
        return initial

    def form_valid(self, form):
        f = MachineRegistrationRequest.objects.filter(
            mac_address=form.cleaned_data["mac_address"]
        )
        if f.exists():
            f.delete()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "request" not in self.request.GET:
            context["registration_requests"] = MachineRegistrationRequest.objects.all()
        return context


class MachineUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "machines.change_machine"

    def get_title(self):
        return _(f"Edit {self.object.name}")

    model = Machine
    template_name = "machine_form.html"
    form_class = MachineForm
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        return context


class MachineConfigureView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "machines.change_machine"

    model = Machine
    template_name = "machine_configure_form.html"
    form_class = ConfigureMachineForm
    context_object_name = "machine"

    def get_title(self):
        return _(f"Configure {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formset"] = (
            kwargs["formset"]
            if "formset" in kwargs
            else MachineTimeFormset(
                prefix="times", queryset=context["machine"].times.all()
            )
        )
        return context

    def form_valid(self, form):
        formset = MachineTimeFormset(prefix="times", data=self.request.POST)
        if formset.is_valid():
            self.object = form.save()
            instances = formset.save(commit=False)
            for instance in instances:
                instance.machine = self.object
                instance.save()
            return super().form_valid(form)
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


class MachineDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "machines.delete_machine"

    model = Machine
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("machines:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")


class MachineStatusPartialView(PermissionRequiredMixin, DetailView):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_status_partial.html"
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status"] = get_socket_data(self.object.pk, "status")
        return context


class MachineLogView(PartialMixin, PermissionRequiredMixin, DetailView):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_log_modal.html"
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class MachineToggleActiveView(BaseToggleActiveView):
    permission_required = "machines.change_machine"
    model = Machine


class MachineQualificationsListView(BaseListView):
    permission_required = "people.view_qualification"
    model = Qualification
    template_name = "machine_qualifications_list.html"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Machine.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualifications for {self.get_object().name}")

    def get_queryset(self):
        queryset = (
            Qualification.objects.filter(machine=self.kwargs["pk"])
            .select_related("person")
            .all()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["machine"] = self.get_object()
        context["qualifications"] = context["page_obj"]
        return context


class MachineInstructorListView(BaseListView):
    permission_required = "people.view_instructor"
    model = Instructor
    template_name = "machine_instructor_list.html"
    context_object_name = "instructors"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Machine.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Instructors for {self.get_object().name}")

    def get_queryset(self):
        queryset = (
            Instructor.objects.filter(machine=self.kwargs["pk"])
            .select_related("person")
            .all()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["machine"] = self.get_object()
        context["instructors"] = context["page_obj"]
        return context


class MachineStatisticsView(
    TitleMixin, PartialMixin, PermissionRequiredMixin, DetailView
):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_statistics.html"

    def get_title(self):
        return _(f"Statistics for {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        days = int(self.request.GET.get("days", 90))
        timeframe_start = datetime.now() - timedelta(days=days)
        query = AccessLog.objects.filter(
            machine=self.object, timestamp__gte=timeframe_start, type=LOG_TYPE_ENABLED
        )

        day_counts = (
            query.annotate(day=TruncDay("timestamp"))
            .values("day")
            .annotate(count=Count("id"))
            .all()
        )
        day_map = {}
        for count in day_counts:
            day_map[count["day"].strftime("%d.%m")] = count["count"]
        day_list = []
        for day in range(days):
            date = (timeframe_start + timedelta(days=day)).strftime("%d.%m")
            day_list.append({"day": date, "count": day_map.get(date, 0)})
        context["access_by_day"] = day_list

        hour_map = {}
        counts = (
            query.annotate(hour=TruncHour("timestamp"))
            .values("hour")
            .annotate(count=Count("id"))
            .all()
        )
        for count in counts:
            hour_map[count["hour"].hour] = count["count"]
        hour_list = []
        for hour in range(24):
            hour_list.append({"hour": hour, "count": hour_map.get(hour, 0)})
        context["access_by_hour"] = hour_list

        weekday_map = {}
        counts = (
            query.annotate(weekday=ExtractWeekDay("timestamp"))
            .values("weekday")
            .annotate(count=Count("id"))
            .all()
        )
        for count in counts:
            index = count["weekday"] - 1
            if index == 0:
                index = 7
            weekday_map[index] = count["count"]
        weekday_list = []
        weekdays = [
            _("Monday"),
            _("Tuesday"),
            _("Wednesday"),
            _("Thursday"),
            _("Friday"),
            _("Saturday"),
            _("Sunday"),
        ]
        for weekday in range(1, 8):
            weekday_list.append(
                {"weekday": weekdays[weekday - 1], "count": weekday_map.get(weekday, 0)}
            )
        context["access_by_weekday"] = weekday_list

        context["selected_days"] = days
        context["days_choices"] = [
            (7, _("7 Days")),
            (30, _("30 Days")),
            (90, _("90 Days")),
            (365, _("365 Days")),
        ]
        return context


class QualifyMachineView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "people.qualify_person"

    model = Qualification
    template_name = "qualify_person.html"
    form_class = QualifyPersonForm

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Machine.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualify for {self.get_object().name}")

    def get_initial(self):
        return {"machine": self.kwargs["pk"]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["machine"] = self.get_object()
        print(context)
        return context

    def get_success_url(self):
        return reverse_lazy("machines:detail", kwargs={"pk": self.kwargs["pk"]})


class AddInstructorMachineView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "people.change_instructors"

    model = Instructor
    template_name = "instructor_person.html"
    form_class = InstructorForm

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Machine.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Add Instructor for {self.get_object().name}")

    def get_initial(self):
        return {"machine": self.kwargs["pk"]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["machine"] = self.get_object()
        return context

    def get_success_url(self):
        return reverse_lazy("machines:detail", kwargs={"pk": self.kwargs["pk"]})


class MachineRegistrationRequestDeleteView(
    TitleMixin, PermissionRequiredMixin, DeleteView
):
    permission_required = "machines.delete_machineregistrationrequest"

    model = Machine
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("machines:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")
