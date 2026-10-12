import logging
from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView,
    View,
)
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from access_log.views import SubjectStatisticsView
from base.utils import get_int_list
from base.views import BaseToggleActiveView, BaseListView, PartialMixin, TitleMixin
from comments.views import CommentCreateView
from comments.forms import CommentForm
from machines.models import Machine
from .models import Person, Qualification
from .conf import PERSON_LOGIN_CODE_VALID_MINUTES
from .forms import (
    PersonForm,
    QualifyPersonForm,
    BulkQualifyForm,
    SelfServiceCodeForm,
    SelfServiceLoginForm,
)
from .self_service import (
    PENDING_EMAIL_SESSION_KEY,
    build_qualification_rows,
    get_logged_in_person,
    login_person,
    logout_person,
    send_login_code,
)
from .services import bulk_qualify
from .filters import PersonFilterSet

logger = logging.getLogger(__name__)


PEOPLE_SORT_CHOICES = (
    ("member_id", _("Member ID")),
    ("name", _("Name")),
    ("email", _("E-Email")),
    ("-updated", _("Last Modified")),
    ("-created", _("Created")),
)

PEOPLE_SORT_CHOICES_KEYS = [choice[0] for choice in PEOPLE_SORT_CHOICES]


class PersonListView(BaseListView):
    permission_required = "people.view_person"

    model = Person
    queryset = Person.objects.values(
        "pk", "name", "email", "is_active", "member_id"
    ).all()
    template_name = "person_list.html"
    context_object_name = "people"
    sort_fields = PEOPLE_SORT_CHOICES_KEYS
    filterset_class = PersonFilterSet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sort_choices"] = PEOPLE_SORT_CHOICES
        return context


class PersonDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "people.view_person"

    model = Person
    template_name = "person_detail.html"
    context_object_name = "person"

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("people.change_person")
        context["can_delete"] = self.request.user.has_perm("people.delete_person")
        context["comment_form"] = CommentForm()
        qualifications = (
            self.object.qualifications.select_related("machine")
            .select_related("instructed_by")
            .all()
        )
        qualifications_paginator = Paginator(
            qualifications, self.request.user.page_length
        )
        context["qualifications"] = qualifications_paginator.get_page(1)
        return context


class PersonStatisticsView(SubjectStatisticsView):
    permission_required = ("people.view_person", "access_log.view_accesslog")

    model = Person
    statistics_scope = "person"


class PersonPublicDetailView(View):
    """The link from the sign-in e-mail: signs the person in and shows their page."""

    def get(self, request, *args, **kwargs):
        person = get_object_or_404(Person, detail_key=self.kwargs["key"], is_active=True)
        if not person.detail_key_valid:
            raise PermissionDenied(_("This link has expired."))
        login_person(request, person)
        return redirect("people:me")


class SelfServiceMixin(TitleMixin):
    def dispatch(self, request, *args, **kwargs):
        self.person = get_logged_in_person(request)
        return super().dispatch(request, *args, **kwargs)


class SelfServiceLoginView(SelfServiceMixin, FormView):
    title = _("Sign in")
    template_name = "self_service_login.html"
    form_class = SelfServiceLoginForm

    def get(self, request, *args, **kwargs):
        if self.person is not None:
            return redirect("people:me")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        person = Person.objects.filter(email__iexact=email, is_active=True).first()
        # Same response whether or not the address is known, so this can't be
        # used to find out who is a member.
        if person is not None and person.can_send_login_code:
            try:
                send_login_code(self.request, person)
            except Exception:
                logger.exception("Failed to send login code to %s", person)
        self.request.session[PENDING_EMAIL_SESSION_KEY] = email
        return redirect("people:me-verify")


class SelfServiceVerifyView(SelfServiceMixin, FormView):
    title = _("Enter code")
    template_name = "self_service_verify.html"
    form_class = SelfServiceCodeForm

    def dispatch(self, request, *args, **kwargs):
        self.email = request.session.get(PENDING_EMAIL_SESSION_KEY)
        if not self.email:
            return redirect("people:me-login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.email
        context["valid_minutes"] = PERSON_LOGIN_CODE_VALID_MINUTES
        return context

    def form_valid(self, form):
        person = Person.objects.filter(email__iexact=self.email, is_active=True).first()
        if person is None or not person.check_login_code(form.cleaned_data["code"]):
            form.add_error(
                "code",
                _("This code is wrong or has expired. Check the e-mail or request a new code."),
            )
            return self.form_invalid(form)
        login_person(self.request, person)
        return redirect("people:me")


class SelfServiceLogoutView(View):
    def post(self, request, *args, **kwargs):
        person = get_logged_in_person(request)
        if person is not None:
            # Also invalidate the e-mailed link, so it can't sign in again.
            person.expire_detail_key()
        logout_person(request)
        return redirect("people:me-login")


class MyQualificationsView(SelfServiceMixin, TemplateView):
    template_name = "self_service_qualifications.html"

    def get(self, request, *args, **kwargs):
        if self.person is None:
            return redirect("people:me-login")
        # Show the page in the person's language rather than the site default.
        translation.activate(self.person.language)
        return super().get(request, *args, **kwargs)

    def get_title(self):
        return self.person.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.person
        context["rows"] = build_qualification_rows(self.person)
        return context


class PersonCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    title = _("Create Person")
    permission_required = "people.add_person"

    model = Person
    template_name = "base_form.html"
    form_class = PersonForm


class PersonUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "people.change_person"

    model = Person
    template_name = "base_form.html"
    form_class = PersonForm
    context_object_name = "person"

    def get_title(self):
        return _(f"Edit {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("people.delete_person")
        return context


class PersonDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "people.delete_person"

    model = Person
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("people:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")


class PersonToggleActiveView(BaseToggleActiveView):
    permission_required = "people.change_person"
    model = Person


class QualifyPersonView(TitleMixin, PartialMixin, PermissionRequiredMixin, FormView):
    permission_required = "people.qualify_person"

    template_name = "qualify_bulk.html"
    form_class = BulkQualifyForm
    full_base_template = "base_slim.html"
    partial_base_template = "partial_base_modal.html"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = get_object_or_404(Person, pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualify {self.get_object().name}")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_object()
        if self.request.method == "POST":
            context["selected_machines"] = Machine.objects.filter(
                pk__in=get_int_list(self.request.POST, "machine_ids")
            )
        return context

    def form_valid(self, form):
        if not self.get_object().is_active:
            form.add_error(None, _("Inactive people cannot be qualified."))
            return self.form_invalid(form)
        machines = Machine.objects.filter(
            pk__in=get_int_list(self.request.POST, "machine_ids"),
            needs_qualification=True,
            state=Machine.MachineStatus.ACTIVE,
        ).exclude(type=Machine.MachineType.LOCK_GROUP)
        if not machines:
            form.add_error(None, _("Select at least one machine."))
            return self.form_invalid(form)
        # With a single machine the form only offers that machine's instructors.
        instructed_by = form.cleaned_data.get("instructed_by")
        if (
            instructed_by is not None
            and len(machines) == 1
            and not machines[0].instructors.filter(person=instructed_by).exists()
        ):
            form.add_error(
                "instructed_by", _("This person is not an instructor for this machine.")
            )
            return self.form_invalid(form)
        bulk_qualify(person=self.get_object(), machines=machines, **form.cleaned_data)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class RevokeQualificationPersonView(
    TitleMixin, PartialMixin, PermissionRequiredMixin, DeleteView
):
    permission_required = "people.qualify_person"

    model = Qualification
    full_base_template = "base_slim.html"
    partial_base_template = "partial_base_modal.html"
    template_name = "revoke_qualification_confirm.html"

    person = None

    def get_person(self):
        if self.person is None:
            self.person = get_object_or_404(Person, pk=self.kwargs["pk"])
        return self.person

    def get_title(self):
        return _(f"Revoke Qualification for {self.get_person().name}")

    def get_object(self, queryset=None):
        return get_object_or_404(
            self.model, person=self.kwargs["pk"], pk=self.kwargs["qualification"]
        )

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class EditQualificationPersonView(TitleMixin, PartialMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "people.qualify_person"

    model = Qualification
    form_class = QualifyPersonForm
    template_name = "qualify_person.html"
    full_base_template = "base_slim.html"
    partial_base_template = "partial_base_modal.html"

    person = None

    def get_person(self):
        if self.person is None:
            self.person = get_object_or_404(Person, pk=self.kwargs["pk"])
        return self.person

    def get_title(self):
        return _(f"Edit Qualification for {self.get_person().name}")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        return get_object_or_404(
            self.model, person=self.kwargs["pk"], pk=self.kwargs["qualification"]
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_person()
        context["machine"] = context["form"].instance.machine
        return context

    def get_success_url(self):
        return reverse_lazy("people:detail", kwargs={"pk": self.kwargs["pk"]})


class PersonQualificationsListView(BaseListView):
    permission_required = "people.view_qualification"
    model = Qualification
    template_name = "person_qualifications_list.html"

    object = None

    def get_object(self):
        if self.object is None:
            self.object = get_object_or_404(Person, pk=self.kwargs["pk"])
        return self.object

    def get_title(self):
        return _(f"Qualifications for {self.get_object().name}")

    def get_queryset(self):
        queryset = (
            Qualification.objects.filter(person=self.kwargs["pk"])
            .select_related("machine", "instructed_by")
            .all()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.get_object()
        context["qualifications"] = context["page_obj"]
        return context

class PersonPopoverView(PermissionRequiredMixin, TemplateView):
    permission_required = "people.view_person"
    template_name = "person_popover.html"
    model = Person

    def get_queryset(self) -> QuerySet[Any]:
        return Person.objects.filter(pk=self.request.GET["person_pk"])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_queryset().get()
        return context
    
class PersonCommentCreateView(CommentCreateView):
    permission_required = "people.comment_person"
    content_model = Person