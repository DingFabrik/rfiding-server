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
from django.urls import reverse_lazy

from tokens.models import Token
from machines.models import Machine
from people.models import Person
from users.models import RFIDingUser
from .forms import UserForm

@method_decorator(login_required, name="dispatch")
class ProfileView(UpdateView):
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
class HomeView(TemplateView):
    template_name = "home.html"

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


class UserListView(ListView, PermissionRequiredMixin):
    permission_required = "users.view_rfidinguser"

    model = RFIDingUser
    template_name = "user_list.html"
    context_object_name = "users"


class UserCreateView(CreateView, PermissionRequiredMixin):
    permission_required = "users.add_rfidinguser"

    model = RFIDingUser
    form_class = UserForm
    template_name = "user_form.html"
    success_url = reverse_lazy("users:list")


class UserUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = "users.change_rfidinguser"

    model = RFIDingUser
    form_class = UserForm
    template_name = "user_form.html"
    success_url = reverse_lazy("users:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.has_perm("users.delete_rfidinguser")
        return context

class UserDetailView(DetailView, PermissionRequiredMixin):
    permission_required = "users.change_rfidinguser"
    model = RFIDingUser
    template_name = "user_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = self.request.user.has_perm("users.change_rfidinguser")
        context["can_delete"] = self.request.user.has_perm("users.delete_rfidinguser")
        return context


class UserDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = "users.delete_rfidinguser"

    model = RFIDingUser
    template_name = "user_delete.html"
    success_url = reverse_lazy("users:list")


class ChangePasswordView(PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")
    template_name = "change_password.html"
    
class AdminChangePasswordView(FormView):
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
