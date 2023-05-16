from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from people.forms import PersonForm

from people.models import Person

class PersonListView(ListView):
    model = Person

class PersonDetailView(DetailView):
    model = Person

class PersonCreateView(CreateView):
    model = Person
    form_class = PersonForm


class PersonUpdateView(UpdateView):
    model = Person
    form_class = PersonForm