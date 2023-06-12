from typing import Any
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import FormView
from django.contrib.auth import get_user_model
from base.forms import InitialSetupForm
from django.contrib.auth import login


class InitialSetupView(FormView):
    form_class = InitialSetupForm
    template_name = "setup.html"
    success_url = reverse_lazy('home_view')

    def get(self, request, *args, **kwargs):
        if get_user_model().objects.all().count() > 0:
            raise PermissionError()
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = get_user_model()()
        user.username = form.data['admin_username']
        user.set_password(form.data['admin_password'])
        user.save()
        login(self.request, user)
        return response