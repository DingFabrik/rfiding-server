from typing import Any, Optional
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic.detail import DetailView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView

from users.models import RfidingUser

class HomeView(LoginRequiredMixin, DetailView):
    model = get_user_model()
    template_name = "home.html"

    def get_object(self):
        return self.request.user
    
class RfiDingLoginView(LoginView):
    def get(self, request, *args, **kwargs):
        if get_user_model().objects.all().count() == 0:
            return redirect(reverse("initial-setup"))
        return super().get(request, *args, **kwargs)