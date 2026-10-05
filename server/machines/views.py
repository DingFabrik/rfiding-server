from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import (
    DetailView,
    RedirectView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView,
)
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from access_log.models import AccessLog
from access_log.statistics import parse_days
from base.views import BaseListView, PartialMixin, TitleMixin
from machines.socket_helper import get_socket_data
from comments.forms import CommentForm
from comments.views import CommentCreateView
from .models import Machine, MachineRegistrationRequest, MachineTime
from .forms import MachineForm, MachineTimeFormset
from .statistics import compute_machine_statistics
from people.models import Qualification, Person
from people.forms import BulkQualifyForm
from people.services import bulk_qualify
from .filters import MachineFilterSet

MACHINE_SORT_CHOICES = (
    ("name", _("Name")),
    ("hostname", _("Hostname")),
    ("ip_address", _("IP-Address")),
    ("mac_address", _("MAC Address")),
    ("-updated", _("Last Modified")),
)
MACHINE_SORT_CHOICES_KEYS = [choice[0] for choice in MACHINE_SORT_CHOICES]

class MachineListView(BaseListView):
    permission_required = "machines.view_machine"
    title = _("Machines")

    model = Machine
    template_name = "machine_list.html"
    context_object_name = "machines"
    sort_fields = MACHINE_SORT_CHOICES_KEYS
    filterset_class = MachineFilterSet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sort_choices"] = MACHINE_SORT_CHOICES
        return context


class MachinePublicDetailView(TitleMixin, DetailView):
    model = Machine
    template_name = "machine_public_detail.html"
    context_object_name = "machine"

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.needs_qualification:
            context["instructors"] = (
                self.object.qualified_people.filter(is_instructor=True)
                .select_related("person")
                .all()
            )
        else:
            context["instructors"] = None
        return context


class MachineDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "machines.view_machine"

    model = Machine
    template_name = "machine_detail.html"
    context_object_name = "machine"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_perm("machines.view_machine") or request.GET.get("public", "false").lower() == "true":
            return MachinePublicDetailView.as_view()(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("machines.change_machine")
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        context["comment_form"] = CommentForm()
        try:
            access = AccessLog.objects.filter(machine=self.object).latest("timestamp")
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
        return context


class MachineSettingsFormMixin:
    """Combined machine settings form: the machine form plus its active times formset."""

    template_name = "machine_form.html"
    form_class = MachineForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["parent"].queryset = Machine.objects.filter(type="lock_group")
        return form

    def get_formset(self):
        queryset = self.object.times.all() if self.object else MachineTime.objects.none()
        data = self.request.POST if self.request.method == "POST" else None
        return MachineTimeFormset(prefix="times", data=data, queryset=queryset)

    def get_sections(self, form, formset):
        sections = []
        for key, label, icon, fields in MachineForm.SECTIONS:
            has_errors = any(form[field].errors for field in fields)
            if key == "schedule" and formset.is_bound:
                has_errors = has_errors or not formset.is_valid()
            sections.append(
                {"key": key, "label": label, "icon": icon, "has_errors": has_errors}
            )
        return sections

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = kwargs.get("formset") or self.get_formset()
        sections = self.get_sections(context["form"], formset)
        context["formset"] = formset
        context["sections"] = sections
        context["active_section"] = next(
            (section["key"] for section in sections if section["has_errors"]),
            "general",
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if "pk" in kwargs else None
        form = self.get_form()
        formset = self.get_formset()
        # Validate both, so errors from every section are shown at once.
        if all([form.is_valid(), formset.is_valid()]):
            return self.form_valid(form, formset)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_valid(self, form, formset):
        response = super().form_valid(form)
        for instance in formset.save(commit=False):
            instance.machine = self.object
            instance.save()
        for instance in formset.deleted_objects:
            instance.delete()
        return response


class MachineCreateView(
    TitleMixin, PermissionRequiredMixin, MachineSettingsFormMixin, CreateView
):
    permission_required = "machines.add_machine"

    def get_title(self):
        return _("Create Machine")

    model = Machine

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

    def form_valid(self, form, formset):
        f = MachineRegistrationRequest.objects.filter(
            mac_address=form.cleaned_data["mac_address"]
        )
        if f.exists():
            f.delete()
        return super().form_valid(form, formset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "request" not in self.request.GET:
            context["registration_requests"] = MachineRegistrationRequest.objects.all()
        return context


class MachineUpdateView(
    TitleMixin, PermissionRequiredMixin, MachineSettingsFormMixin, UpdateView
):
    permission_required = "machines.change_machine"

    def get_title(self):
        return _(f"Edit {self.object.name}")

    model = Machine
    context_object_name = "machine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("machines.delete_machine")
        return context


class MachineConfigureView(PermissionRequiredMixin, RedirectView):
    """The configure page was merged into the edit form."""

    permission_required = "machines.change_machine"

    def get_redirect_url(self, *args, **kwargs):
        return reverse("machines:update", kwargs={"pk": kwargs["pk"]}) + "#schedule"


class MachineDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "machines.delete_machine"

    model = Machine
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("machines:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")

class MachinePopoverView(PermissionRequiredMixin, TemplateView):
    permission_required = "machines.view_machine"
    template_name = "machine_popover.html"
    model = Machine
    
    def get_queryset(self):
        return Machine.objects.filter(pk=self.request.GET["machine_pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_queryset().get()
        try:
            context["last_access"] = AccessLog.objects.filter(machine=context["object"]).latest("timestamp")
        except AccessLog.DoesNotExist:
            context["last_access"] = None
        return context

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
            .select_related("person", "instructed_by")
            .all()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["machine"] = self.get_object()
        context["qualifications"] = context["page_obj"]
        return context


class MachineInstructorListView(BaseListView):
    permission_required = "people.view_qualification"
    model = Qualification
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
            Qualification.objects.filter(machine=self.kwargs["pk"], is_instructor=True)
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
        days = parse_days(self.request.GET.get("days"))
        context.update(compute_machine_statistics(self.object, days))
        return context


class QualifyMachineView(TitleMixin, PartialMixin, PermissionRequiredMixin, FormView):
    permission_required = "people.qualify_person"

    template_name = "qualify_bulk.html"
    form_class = BulkQualifyForm
    full_base_template = "base_slim.html"
    partial_base_template = "partial_base_modal.html"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = Machine.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualify for {self.get_object().name}")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["machine"] = self.get_object()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["machine"] = self.get_object()
        if self.request.method == "POST":
            context["selected_people"] = Person.objects.filter(
                pk__in=self.request.POST.getlist("person_ids")
            )
        return context

    def form_valid(self, form):
        people = Person.objects.filter(
            pk__in=self.request.POST.getlist("person_ids"), is_active=True
        )
        if not people:
            form.add_error(None, _("Select at least one person."))
            return self.form_invalid(form)
        bulk_qualify(machine=self.get_object(), people=people, **form.cleaned_data)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("machines:detail", kwargs={"pk": self.kwargs["pk"]})

class MachineRegistrationRequestDeleteView(
    TitleMixin, PermissionRequiredMixin, DeleteView
):
    permission_required = "machines.delete_machineregistrationrequest"

    model = MachineRegistrationRequest
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("machines:create")

    def get_title(self):
        return _(f"Delete {self.object.mac_address}")

class MachineCommentCreateView(CommentCreateView):
    permission_required = "machines.comment_machine"
    content_model = Machine