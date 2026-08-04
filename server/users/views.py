from django.forms.forms import BaseForm
from django.http import HttpResponse
from django.views.generic import (
    TemplateView,
    UpdateView,
    CreateView,
    DeleteView,
    DetailView,
    FormView,
)
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.forms import PasswordChangeForm, AdminPasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render

from base.views import TitleMixin, BaseListView, PartialMixin
from .widgets import WidgetDataProvider
from users.models import RFIDingUser, UserWidget
from .forms import UserForm, GroupForm, ProfileForm, UserWidgetForm


@method_decorator(login_required, name="dispatch")
class ProfileView(TitleMixin, UpdateView):
    title = _("Profile")
    model = RFIDingUser
    template_name = "profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("users:profile")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


@method_decorator(login_required, name="dispatch")
class HomeView(TitleMixin, TemplateView):
    template_name = "home.html"
    title = _("Home")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["widgets"] = self.request.user.widgets.all()
        return context

@method_decorator(login_required, name="dispatch")
class HomeWidgetsView(TemplateView):
    template_name = "home_widgets.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "widget_id" in self.request.GET:
            widgets = UserWidget.objects.filter(pk=self.request.GET["widget_id"])
        else:
            widgets = self.request.user.widgets.all()
        data_provider = WidgetDataProvider()
        data_provider.provide_for_widgets(widgets)
        context["widgets"] = widgets
        return context


class ChangePasswordView(TitleMixin, PasswordChangeView):
    title = _("Change Password")
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")
    template_name = "change_password.html"


class UserListView(BaseListView):
    permission_required = "users.view_rfidinguser"

    model = RFIDingUser
    template_name = "user_list.html"
    context_object_name = "users"


class UserCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    title = _("Create User")
    permission_required = "users.add_rfidinguser"

    model = RFIDingUser
    form_class = UserForm
    template_name = "user_form.html"
    success_url = reverse_lazy("users:list")


class UserUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "users.change_rfidinguser"

    model = RFIDingUser
    form_class = UserForm
    template_name = "user_form.html"
    success_url = reverse_lazy("users:list")

    def get_title(self):
        return _(f"Edit {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("users.delete_rfidinguser")
        return context


class UserDetailView(TitleMixin, PermissionRequiredMixin, DetailView):
    permission_required = "users.change_rfidinguser"
    model = RFIDingUser
    template_name = "user_detail.html"

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("users.change_rfidinguser")
        context["can_delete"] = self.request.user.has_perm("users.delete_rfidinguser")
        return context


class UserDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "users.delete_rfidinguser"

    def get_title(self):
        return _(f"Delete {self.object.name}")

    model = RFIDingUser
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("users:list")


class AdminChangePasswordView(TitleMixin, FormView):
    title = _("Change Password")
    form_class = AdminPasswordChangeForm
    template_name = "change_password.html"
    success_url = reverse_lazy("users:list")

    def get_object(self):
        return RFIDingUser.objects.get(pk=self.kwargs["pk"])

    def get_form(self) -> BaseForm:
        if self.request.POST:
            return AdminPasswordChangeForm(
                user=self.get_object(), data=self.request.POST
            )
        return AdminPasswordChangeForm(user=self.get_object())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        return context


class GroupListView(BaseListView):
    permission_required = "auth.view_group"
    title = _("Groups")

    model = Group
    template_name = "group_list.html"
    context_object_name = "groups"


class GroupCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
    permission_required = "auth.add_group"
    title = _("Create Group")

    model = Group
    form_class = GroupForm
    template_name = "base_form.html"
    success_url = reverse_lazy("users:groups:list")


class GroupUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "auth.change_group"

    model = Group
    form_class = GroupForm
    template_name = "base_form.html"
    success_url = reverse_lazy("users:groups:list")

    def get_title(self):
        return _(f"Edit {self.object.name}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("auth.delete_group")
        return context


class GroupDeleteView(TitleMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "auth.delete_group"

    model = Group
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("users:groups:list")

    def get_title(self):
        return _(f"Delete {self.object.name}")
    
@method_decorator(login_required, name="dispatch")
class WidgetCreateView(TitleMixin, PartialMixin, CreateView):
    title = _("Add Widget")

    model = UserWidget
    form_class = UserWidgetForm
    template_name = "widget_form.html"
    success_url = reverse_lazy("home")
    partial_base_template = "partial_base_form.html"
    full_base_template = "base_form.html"
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        redirect = super().form_valid(form)
        widget = self.object
        if self.is_partial:
            context = {}
            context["widget"] = widget
            provider = WidgetDataProvider()
            provider.provide_for_widgets([widget])
            
            response = render(self.request, widget.template, context)
            response["HX-Reswap"] = "beforeend"
            return response
        return redirect
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_url"] = reverse_lazy("users:widgets:create")
        return context
    
@method_decorator(login_required, name="dispatch")
class WidgetUpdateView(TitleMixin, PartialMixin, UpdateView):
    title = _("Add Widget")

    model = UserWidget
    form_class = UserWidgetForm
    template_name = "widget_form.html"
    success_url = reverse_lazy("home")
    partial_base_template = "partial_base_form.html"
    full_base_template = "base_form.html"
    
    def form_valid(self, form):
        redirect = super().form_valid(form)
        widget = self.object
        if self.is_partial:
            context = {}
            provider = WidgetDataProvider()
            provider.provide_for_widgets([widget])
            context["widget"] = widget
            
            response = render(self.request, widget.template, context)
            response["HX-Retarget"] = "#widget-" + str(widget.pk)
            response["HX-Reswap"] = "outerHTML"
            return response
        return redirect
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_url"] = reverse_lazy("users:widgets:update", kwargs={"pk": self.kwargs["pk"]})
        return context

@method_decorator(login_required, name="dispatch")
class WidgetDeleteView(TitleMixin, DeleteView):
    model = UserWidget
    template_name = "delete_confirm.html"
    success_url = reverse_lazy("home")

    def get_title(self):
        return _(f"Delete {self.object.name}")
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.form_valid(self.get_form())
    
    def form_valid(self, form):
        self.object.delete()
        return HttpResponse(status=200)