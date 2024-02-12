from django.shortcuts import render
from django.views.generic import TemplateView
import subprocess
import platform
import django
from django.contrib.auth.mixins import PermissionRequiredMixin

from rfiding import settings

class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['version'] = settings.VERSION
        context['python_version'] = platform.python_version()
        context['django_version'] = django.get_version()
        return context
    
    
class BaseToggleActiveView(TemplateView, PermissionRequiredMixin):
    template_name = 'snippets/active_toggle.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        object = self.model.objects.get(pk=self.kwargs['pk'])
        object.is_active = not object.is_active
        object.save()
        context['object'] = object
        return context