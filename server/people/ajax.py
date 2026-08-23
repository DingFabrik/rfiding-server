from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from django.db.models import Q

from .models import Person

AUTOCOMPLETE_RESULT_LIMIT = 20


class HasViewPersonPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.has_perm("people.view_person"))


def get_people(request, term):
    if not term:
        return Person.objects.none()
    return Person.objects.filter(Q(name__icontains=term) | Q(email__icontains=term))

class PersonAutocompleteView(APIView):
    queryset = Person.objects.all()
    permission_classes = [HasViewPersonPermission]

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)[:AUTOCOMPLETE_RESULT_LIMIT]
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
    permission_classes = [HasViewPersonPermission]

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)
        people = people.exclude(qualifications__machine__id=machine)[
            :AUTOCOMPLETE_RESULT_LIMIT
        ]
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
    permission_classes = [HasViewPersonPermission]

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)
        people = people.exclude(
            qualifications__machine_id=machine, qualifications__is_instructor=True
        )[:AUTOCOMPLETE_RESULT_LIMIT]
        return Response(
            [
                {"value": person.id, "label": f"{person.name} ({person.email})"}
                for person in people
            ],
            status=status.HTTP_200_OK,
        )
