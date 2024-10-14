from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.views.generic import (
    ListView,
    TemplateView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.views import BaseToggleActiveView, PartialListMixin
from .models import Token, UnknownToken
from .forms import TokenForm
from people.models import Person


TOKEN_SORT_CHOICES = (
    ("pk", _("Default")),
    ("serial", _("Serial")),
    ("purpose", _("Purpose")),
    ("-updated", _("Last Modified")),
)

TOKEN_SORT_CHOICES_KEYS = [choice[0] for choice in TOKEN_SORT_CHOICES]

class TokenListView(PartialListMixin, ListView, PermissionRequiredMixin):
    queryset = Token.objects.select_related("person").filter(archived=None).order_by("id")
    permission_required = "tokens.view_token"

    model = Token
    template_name = "token_list.html"
    context_object_name = "tokens"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(serial__icontains=search)
        sort = self.request.GET.get("sort")
        if sort in TOKEN_SORT_CHOICES_KEYS:
            queryset = queryset.order_by(sort)
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("tokens.create_token")
        context["model"] = self.model
        context["sort_choices"] = TOKEN_SORT_CHOICES
        return context


class UnknownTokenListView(ListView, PermissionRequiredMixin):
    permission_required = "tokens.view_unknown_token"

    model = UnknownToken
    template_name = "unknown_token_list.html"
    context_object_name = "tokens"


class ClearUnknownTokensView(View, PermissionRequiredMixin):
    permission_required = "tokens.delete_unknown_token"

    def get(self, request):
        UnknownToken.objects.all().delete()
        return redirect("tokens:unknown")


class AssignTokenView(CreateView, PermissionRequiredMixin):
    permission_required = "tokens.create_token"

    model = Token
    template_name = "token_form.html"
    form_class = TokenForm

    def get_initial(self):
        initial = super().get_initial()
        initial["serial"] = self.kwargs["serial"]
        return initial

    def form_valid(self, form):
        r = super().form_valid(form)
        unknown_token = UnknownToken.objects.filter(serial=form.instance.serial)
        if unknown_token.exists():
            unknown_token.delete()
        return r

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["prefilled_serial"] = True
        return context


class TokenDetailView(DetailView, PermissionRequiredMixin):
    permission_required = "tokens.view_token"

    model = Token
    template_name = "token_detail.html"
    context_object_name = "token"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("tokens.change_token")
        context["can_delete"] = self.request.user.has_perm("tokens.delete_token")
        return context


class TokenCreateView(CreateView, PermissionRequiredMixin):
    permission_required = "tokens.add_token"

    model = Token
    template_name = "token_form.html"
    form_class = TokenForm
    success_url = reverse_lazy("tokens:list")


class TokenUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = "tokens.change_token"

    model = Token
    template_name = "token_form.html"
    form_class = TokenForm
    context_object_name = "token"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("tokens.delete_token")
        return context


class TokenArchiveView(DeleteView, PermissionRequiredMixin):
    permission_required = "tokens.delete_token"

    model = Token
    template_name = "archive_confirm.html"
    success_url = reverse_lazy("tokens:list")
    
    def handle(self):
        token = self.get_object()
        token.is_active = False
        token.archived = timezone.now()
        token.save()
        return redirect(self.success_url)
    
    def delete(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return self.handle()

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return self.handle()


class TokenToggleActiveView(BaseToggleActiveView):
    permission_required = "tokens.change_token"
    model = Token

class PersonForTokenPopoverView(TemplateView):
    template_name = "person_popover.html"
    model = Person

    def get_queryset(self) -> QuerySet[Any]:
        return Person.objects.filter(token__pk=self.request.GET["token_pk"])
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_queryset().get()
        return context