from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from machines.models import Machine

class MachineListView(ListView):
    model = Machine

class MachineDetailView(DetailView):
    model = Machine