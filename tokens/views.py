from typing import Any
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import redirect

from base.views import BaseToggleActiveView
from .models import Token, UnknownToken
from .forms import TokenForm

class TokenListView(ListView, PermissionRequiredMixin):
    queryset = Token.objects.select_related('person').all().order_by('id')
    permission_required = 'tokens.view_token'

    model = Token
    template_name = 'token_list.html'
    context_object_name = 'tokens'

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(serial__icontains=search)
        return queryset

    def get_paginate_by(self, queryset):
        return self.request.user.page_length

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = self.request.user.has_perm("tokens.create_token")
        context["model"] = self.model
        return context
    
class UnknownTokenListView(ListView, PermissionRequiredMixin):
    permission_required = 'tokens.view_unknown_token'

    model = UnknownToken
    template_name = 'unknown_token_list.html'
    context_object_name = 'tokens'

class ClearUnknownTokensView(View, PermissionRequiredMixin):
    permission_required = 'tokens.delete_unknown_token'

    def get(self, request):
        UnknownToken.objects.all().delete()
        return redirect('tokens:unknown')

class AssignTokenView(CreateView, PermissionRequiredMixin):
    permission_required = 'tokens.create_token'

    model = Token
    template_name = 'token_form.html'
    form_class = TokenForm

    def get_initial(self):
        initial = super().get_initial()
        initial['serial'] = self.kwargs['serial']
        return initial
    
    def form_valid(self, form):
        r = super().form_valid(form)
        unknown_token = UnknownToken.objects.filter(serial=form.instance.serial)
        if unknown_token.exists():
            unknown_token.delete()
        return r
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['prefilled_serial'] = True
        return context

class TokenDetailView(DetailView, PermissionRequiredMixin):
    permission_required = 'tokens.view_token'

    model = Token
    template_name = 'token_detail.html'
    context_object_name = 'token'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.request.user.has_perm('tokens.change_token')
        context['can_delete'] = self.request.user.has_perm('tokens.delete_token')
        return context

class TokenCreateView(CreateView, PermissionRequiredMixin):
    permission_required = 'tokens.add_token'

    model = Token
    template_name = 'token_form.html'
    form_class = TokenForm
    success_url = reverse_lazy('tokens:list')

class TokenUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = 'tokens.change_token'

    model = Token
    template_name = 'token_form.html'
    form_class = TokenForm
    context_object_name = 'token'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete'] = self.request.user.has_perm('tokens.delete_token')
        return context

class TokenDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = 'tokens.delete_token'

    model = Token
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('tokens:list')

class TokenToggleActiveView(BaseToggleActiveView):
    permission_required = 'tokens.change_token'
    model = Token