from typing import Any, Optional
from django.db import models
from django.shortcuts import render
from django.views.generic.detail import DetailView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import RfidingUser

class HomeView(LoginRequiredMixin, DetailView):
    model = get_user_model()
    template_name = "home.html"

    def get_object(self):
        return self.request.user
    
    