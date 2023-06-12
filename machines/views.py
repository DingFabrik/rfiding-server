from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from machines.forms import MachineForm

from machines.models import Machine

class MachineListView(ListView):
    model = Machine

class MachineDetailView(DetailView):
    model = Machine

class MachineCreateView(CreateView):
    model = Machine
    form_class = MachineForm


class MachineUpdateView(UpdateView):
    model = Machine
    form_class = MachineForm