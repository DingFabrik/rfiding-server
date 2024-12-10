from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import (
    ListView,
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
from base.views import BaseToggleActiveView, PartialListMixin, PartialMixin
from .models import Machine
from .forms import MachineForm, ConfigureMachineForm, MachineTimeFormset
from people.models import Qualification, Instructor

MACHINE_SORT_CHOICES = (
    ("pk", _("Default")),
    ("name", _("Name")),
    ("hostname", _("Hostname")),
    ("ip_address", _("IP Address")),
    ("mac_address", _("MAC Address")),
    ("-updated", _("Last Modified")),
)

MACHINE_SORT_CHOICES_KEYS = [choice[0] for choice in MACHINE_SORT_CHOICES]

class MachineListView(PartialListMixin, PermissionRequiredMixin, ListView):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_list.html"
    context_object_name = "machines"

    def get_queryset(self):
        queryset = super().get_queryset().filter(completed_setup=True)
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        sort = self.request.GET.get("sort")
        if sort in MACHINE_SORT_CHOICES_KEYS:
            queryset = queryset.order_by(sort)
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("machines.create_machine")
        context["model"] = self.model
        context["sort_choices"] = MACHINE_SORT_CHOICES
        return context


class MachineDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_detail.html"
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("machines.change_machine")
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        try:
            access = AccessLog.objects.filter(
                machine=self.object
            ).latest("-timestamp")
            context["last_access"] = access.timestamp
        except AccessLog.DoesNotExist:
            context["last_access"] = None
        if self.object.needs_qualification:
            qualifications = (
                self.object.qualified_people
                .select_related("person")
                .select_related("instructed_by")
                .all()
            )
            qualifications_paginator = Paginator(qualifications, self.request.user.page_length)
            context["qualifications"] = qualifications_paginator.get_page(1)
            context["qualifications_count"] = qualifications_paginator.count
            instructors = self.object.instructors.select_related("person").all()
            instructors_paginator = Paginator(instructors, self.request.user.page_length)
            context["instructors"] = instructors_paginator.get_page(1)
            context["instructors_count"] = instructors_paginator.count
        return context


class MachineCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "machines.add_machine"

    model = Machine
    template_name = "machine_form.html"
    form_class = MachineForm
    success_url = reverse_lazy("machines:list")


class MachineUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "machines.change_machine"

    model = Machine
    template_name = "machine_form.html"
    form_class = MachineForm
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        return context


class MachineConfigureView(PermissionRequiredMixin, UpdateView):
    permission_required = "machines.change_machine"

    model = Machine
    template_name = "machine_configure_form.html"
    form_class = ConfigureMachineForm
    context_object_name = "machine"

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


class MachineDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "machines.delete_machine"

    model = Machine
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("machines:list")


class MachineToggleActiveView(BaseToggleActiveView):
    permission_required = "machines.change_machine"
    model = Machine

class MachineQualificationsListView(PartialListMixin, PermissionRequiredMixin, ListView):
    permission_required = "people.view_qualification"
    model = Qualification
    template_name = "machine_qualifications_list.html"

    def get_queryset(self):
        queryset = Qualification.objects.filter(machine=self.kwargs["pk"]).select_related("person").all()
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = Machine.objects.get(pk=self.kwargs["pk"])
        context["qualifications"] = context["page_obj"]
        return context


class MachineInstructorListView(PartialListMixin, PermissionRequiredMixin, ListView):
    permission_required = "people.view_instructor"
    model = Instructor
    template_name = "machine_instructor_list.html"
    context_object_name = "instructors"

    def get_queryset(self):
        queryset = Instructor.objects.filter(machine=self.kwargs["pk"]).select_related("person").all()
        return queryset
    
    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model"] = self.model
        context["machine"] = Machine.objects.get(pk=self.kwargs["pk"])
        context["instructors"] = context["page_obj"]
        return context
    

class MachineStatisticsView(PartialMixin, PermissionRequiredMixin, DetailView):
    permission_required = "machines.view_machine"
    
    model = Machine
    template_name = "machine_statistics.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timeframe_start = datetime.now() - timedelta(days=90)
        query = (AccessLog.objects
                 .filter(machine=self.object,
                         timestamp__gte=timeframe_start,
                         type=LOG_TYPE_ENABLED))

        day_counts = (query
                                    .annotate(day=TruncDay("timestamp"))
                                    .values("day")
                                    .annotate(count=Count("id"))   
                                    .all())
        day_map = {}
        for count in day_counts:
            day_map[count["day"].strftime("%d.%m")] = count["count"]
        day_list = []
        for day in range(90):
            date = (timeframe_start + timedelta(days=day)).strftime("%d.%m")
            day_list.append({"day": date, "count": day_map.get(date, 0)})
        context["access_by_day"] = day_list
        
        hour_map = {}
        counts = (query.annotate(hour=TruncHour("timestamp"))
                        .values("hour")
                        .annotate(count=Count("id"))   
                        .all())
        for count in counts:
            hour_map[count["hour"].hour] = count["count"]
        hour_list = []
        for hour in range(24):
            hour_list.append({"hour": hour, "count": hour_map.get(hour, 0)})
        context["access_by_hour"] = hour_list
        
        weekday_map = {}
        counts = (query.annotate(weekday=ExtractWeekDay("timestamp"))
                        .values("weekday")
                        .annotate(count=Count("id"))   
                        .all())
        for count in counts:
            index = count["weekday"] - 1
            if index == 0:
                index = 7
            weekday_map[index] = count["count"]
        weekday_list = []
        weekdays = [_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")]
        for weekday in range(1, 8):
            weekday_list.append({"weekday": weekdays[weekday-1], "count": weekday_map.get(weekday, 0)})
        context["access_by_weekday"] = weekday_list
        return context