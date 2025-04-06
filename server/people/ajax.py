from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from .models import Person


def get_people(request, term):
    return Person.objects.filter(Q(name__icontains=term) | Q(email__icontains=term))

class PersonAutocompleteView(APIView):
    queryset = Person.objects.all()

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)
        returned = []
        for person in people:
            returned.append(
                {
                    "value": person.id,
                    "label": f"{person.name} ({person.email})",
                }
            )
        return Response(returned, status=status.HTTP_200_OK)

class QualifyablePersonAutocompleteView(APIView):
    queryset = Person.objects.all()

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)
        people = people.exclude(qualifications__machine__id=machine)
        people.select_related("instructors")
        returned = []
        for person in people:
            returned.append(
                {
                    "value": person.id,
                    "label": f"{person.name} ({person.email})",
                }
            )
        return Response(returned, status=status.HTTP_200_OK)


class InstructorPersonAutocompleteView(APIView):
    queryset = Person.objects.all()

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)
        people = people.exclude(can_instruct__machine__id=machine)
        print(people)
        return Response(
            [
                {"value": person.id, "label": f"{person.name} ({person.email})"}
                for person in people
            ],
            status=status.HTTP_200_OK,
        )
