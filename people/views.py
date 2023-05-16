from django.urls import reverse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.base import View
from people.forms import PersonForm
from django.shortcuts import redirect, get_object_or_404

from people.models import Person, Qualification
from machines.models import Machine

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

class AssignQualificationView(View):

    def get(self, *args, **kwargs):
        person = get_object_or_404(Person, pk=kwargs['person'])
        machine = get_object_or_404(Machine, pk=kwargs['machine'])
        existing_qualification = Qualification.objects.filter(person=person, machine=machine)
        if len(existing_qualification) == 0:
            qualification = Qualification()
            qualification.person = person
            qualification.machine = machine
            qualification.save()
        return redirect(reverse("people:detail", kwargs={"pk": person.pk}))
    
class UnassignQualificationView(View):

    def get(self, *args, **kwargs):
        qualification = get_object_or_404(Qualification, person__pk=kwargs['person'], machine__pk=kwargs['machine'])
        qualification.delete()
        return redirect(reverse("person:detail", kwargs={"pk": qualification.person.pk}))