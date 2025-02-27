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
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.views import BaseToggleActiveView, BaseListView
from .models import Token, TokenType, UnknownToken, BlacklistedToken
from .forms import TokenForm
from people.models import Person
from .common import clear_unknown_tokens


TOKEN_SORT_CHOICES = (
    ("serial", _("Serial")),
    ("purpose", _("Purpose")),
    ("-updated", _("Last Modified")),
    ("-created", _("Created")),
)

TOKEN_FILTER_CHOICES = (
    ("active", _("Active")),
    ("inactive", _("Inactive")),
    ("all", _("All")),
    ("archived", _("Archived")),
)

TOKEN_SORT_CHOICES_KEYS = [choice[0] for choice in TOKEN_SORT_CHOICES]

class TokenListView(BaseListView):
    queryset = Token.objects.select_related("person").select_related("type").filter(archived=None).order_by("id")
    permission_required = "tokens.view_token"

    model = Token
    template_name = "token_list.html"
    context_object_name = "tokens"
    search_field = "serial"
    sort_fields = TOKEN_SORT_CHOICES_KEYS

    def get_queryset(self):
        queryset = super().get_queryset()
        filter = self.request.GET.get("filter")
        if filter == "all":
            queryset = queryset
        elif filter == "inactive":
            queryset = queryset.filter(is_active=False)
        elif filter == "archived":
            queryset = queryset.filter(archived__isnull=False)
        else:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sort_choices"] = TOKEN_SORT_CHOICES
        context["filter_choices"] = TOKEN_FILTER_CHOICES
        return context


class UnknownTokenListView(PermissionRequiredMixin, ListView):
    permission_required = "tokens.view_unknown_token"

    model = UnknownToken
    template_name = "unknown_token_list.html"
    context_object_name = "tokens"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create_token"] = self.request.user.has_perm("tokens.create_token")
        context["can_create_blacklistedtoken"] = self.request.user.has_perm("tokens.create_blacklistedtoken")
        return context


class ClearUnknownTokensView(PermissionRequiredMixin, View):
    permission_required = "tokens.delete_unknown_token"

    def get(self, request):
        clear_unknown_tokens()
        return redirect("tokens:unknown")


class AssignTokenView(PermissionRequiredMixin, CreateView):
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


class TokenDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "tokens.view_token"

    model = Token
    template_name = "token_detail.html"
    context_object_name = "token"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("tokens.change_token")
        context["can_delete"] = self.request.user.has_perm("tokens.delete_token")
        return context


class TokenCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "tokens.add_token"

    model = Token
    template_name = "token_form.html"
    form_class = TokenForm


class TokenUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "tokens.change_token"

    model = Token
    template_name = "token_form.html"
    form_class = TokenForm
    context_object_name = "token"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("tokens.delete_token")
        return context


class TokenArchiveView(PermissionRequiredMixin, DeleteView):
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

class PersonForTokenPopoverView(PermissionRequiredMixin, TemplateView):
    permission_required = "people.view_person"
    template_name = "person_popover.html"
    model = Person

    def get_queryset(self) -> QuerySet[Any]:
        return Person.objects.filter(token__pk=self.request.GET["token_pk"])
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_queryset().get()
        return context
    
    
class BlacklistTokenView(PermissionRequiredMixin, View):
    permission_required = "tokens.create_blacklistedtoken"

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        serial = kwargs["serial"]
        UnknownToken.objects.filter(serial=serial).delete()
        BlacklistedToken.objects.create(serial=serial)
        return redirect("tokens:blacklisted")
class BlacklistedTokenListView(BaseListView):
    permission_required = "tokens.view_blacklistedtoken"

    model = BlacklistedToken
    template_name = "blacklisted_token_list.html"
    context_object_name = "tokens"
    
class BlacklistedTokenDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "tokens.delete_blacklistedtoken"
    
    model = BlacklistedToken
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("tokens:blacklisted")
    

class NextFreeTokenLabelView(PermissionRequiredMixin, View):
    permission_required = "tokens.view_token"

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        tokens = Token.objects.filter(label_id__isnull=False)
        def default_label_format_func(x):
            return f"{x}"
        label_format_func = default_label_format_func
        if "type" in request.GET and len(request.GET["type"]) > 0:
            token_type = get_object_or_404(TokenType, pk=request.GET["type"])
            label_format_func = token_type.format_label_id
            tokens = tokens.filter(type=token_type)
        else:
            tokens = tokens.filter(type__isnull=True)
        token = tokens.order_by("-label_id").first()
        if token and token.label_id:
            label_id = token.label_id + 1
        else:
            label_id = 1
        return HttpResponse(_("Next free label: %s") % label_format_func(label_id))
    
class TokenTypeListView(BaseListView):
    permission_required = "tokens.view_tokentype"

    model = TokenType
    template_name = "tokentype_list.html"
    context_object_name = "types"
    
    def get_paginate_by(self, queryset):
        return self.request.user.page_length
    
class TokenTypeCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "tokens.add_tokentype"

    model = TokenType
    template_name = "tokentype_form.html"
    fields = ["name", "description", "label_prefix", "label_id_padding"]
    success_url = reverse_lazy("tokens:types:list")

class TokenTypeUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "tokens.change_tokentype"

    model = TokenType
    template_name = "tokentype_form.html"
    fields = ["name", "description", "label_prefix", "label_id_padding"]
    context_object_name = "type"
    success_url = reverse_lazy("tokens:types:list")

class TokenTypeDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "tokens.delete_tokentype"

    model = TokenType
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("tokens:types:list")
