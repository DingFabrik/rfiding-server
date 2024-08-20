from django.views.generic import TemplateView, UpdateView, ListView, CreateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.conf import settings
from django.urls import reverse_lazy

from tokens.models import Token
from machines.models import Machine
from people.models import Person
from users.models import RFIDingUser

@method_decorator(login_required, name='dispatch')
class ProfileView(UpdateView):
    model = RFIDingUser
    template_name = "profile.html"
    fields = ['name', 'email', 'language', 'page_length']
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

@method_decorator(login_required, name='dispatch')
class HomeView(TemplateView):
    template_name = "home.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activeTokenCount'] = Token.objects.filter(is_active=True).count()
        context['tokenCount'] = Token.objects.count()
        context['activeMachineCount'] = Machine.objects.filter(is_active=True).count()
        context['machineCount'] = Machine.objects.count()
        context['activePeopleCount'] = Person.objects.filter(is_active=True).count()
        context['peopleCount'] = Person.objects.count()
        context['user'] = self.request.user
        return context

class UserListView(ListView, PermissionRequiredMixin):
    permission_required = 'users.view_rfidinguser'

    model = RFIDingUser
    template_name = "user_list.html"
    context_object_name = "users"

class UserCreateView(CreateView, PermissionRequiredMixin):
    permission_required = 'users.add_rfidinguser'

    model = RFIDingUser
    template_name = "user_form.html"
    fields = ['name', 'email']
    success_url = reverse_lazy('users:list')

class UserUpdateView(UpdateView, PermissionRequiredMixin):
    permission_required = 'users.change_rfidinguser'

    model = RFIDingUser
    template_name = "user_form.html"
    fields = ['name', 'email']
    success_url = reverse_lazy('users:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete'] = self.request.user.has_perm('users.delete_rfidinguser')
        return context

class UserDeleteView(DeleteView, PermissionRequiredMixin):
    permission_required = 'users.delete_rfidinguser'

    model = RFIDingUser
    template_name = "user_delete.html"
    success_url = reverse_lazy('users:list')