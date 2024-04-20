from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from base.views import BaseListView
from .models import Firmware
from .forms import FirmwareForm
from django.contrib.auth.mixins import PermissionRequiredMixin

class FirmwareListView(BaseListView, PermissionRequiredMixin):
    template_name = 'firmware_list.html'
    permission_required = 'firmware.view_firmware'
    context_object_name = 'firmware'
    model = Firmware

class FirmwareDetailView(PermissionRequiredMixin, ListView):
    permission_required = 'firmware.view_firmware'
    model = Firmware
    template_name = 'firmware_detail.html'
    context_object_name = 'firmware'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.request.user.has_perm('firmware.change_firmware')
        context['can_delete'] = self.request.user.has_perm('firmware.delete_firmware')
        return context

class FirmwareCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'firmware.add_firmware'
    model = Firmware
    template_name = 'firmware_form.html'
    form_class = FirmwareForm
    success_url = reverse_lazy('firmware:list')

class FirmwareUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'firmware.change_firmware'
    model = Firmware
    template_name = 'firmware_form.html'
    form_class = FirmwareForm
    context_object_name = 'firmware'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete'] = self.request.user.has_perm('firmware.delete_firmware')
        return context

class FirmwareDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'firmware.delete_firmware'
    
    model = Firmware
    template_name = 'delete_confirm.html'
