from django.forms.forms import BaseForm
from django.views.generic import (
    TemplateView,
    UpdateView,
    ListView,
    CreateView,
    DeleteView,
    DetailView,
    FormView
)
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.forms import PasswordChangeForm, AdminPasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.views import TitleMixin
from tokens.models import Token
from machines.models import Machine
from people.models import Person
from users.models import RFIDingUser
from .forms import UserForm, GroupForm

@method_decorator(login_required, name="dispatch")
class ProfileView(TitleMixin, UpdateView):
    title = _("Profile")
    model = RFIDingUser
    template_name = "profile.html"
    fields = ["name", "email", "language", "page_length", "theme_mode", "theme"]
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
        context["activeTokenCount"] = Token.objects.filter(is_active=True).count()
        context["tokenCount"] = Token.objects.count()
        context["activeMachineCount"] = Machine.objects.filter(is_active=True).count()
        context["machineCount"] = Machine.objects.count()
        context["activePeopleCount"] = Person.objects.filter(is_active=True).count()
        context["peopleCount"] = Person.objects.count()
        context["user"] = self.request.user
        return context


class ChangePasswordView(TitleMixin, PasswordChangeView):
    title = _("Change Password")
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")
    template_name = "change_password.html"
    

class UserListView(TitleMixin, PermissionRequiredMixin, ListView):
    title = _("Users")
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
        return _("Edit ${self.object.name}")

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
        return _("Delete ${self.object.name}")

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
            return AdminPasswordChangeForm(user=self.get_object(), data=self.request.POST)
        return AdminPasswordChangeForm(user=self.get_object())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        return context


class GroupListView(TitleMixin, PermissionRequiredMixin, ListView):
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
    template_name = "group_form.html"
    success_url = reverse_lazy("users:groups:list")


class GroupUpdateView(TitleMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "auth.change_group"

    model = Group
    form_class = GroupForm
    template_name = "group_form.html"
    success_url = reverse_lazy("users:groups:list")
    
    def get_title(self):
        return _("Edit ${self.object.name}")

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
        return _("Delete ${self.object.name}")