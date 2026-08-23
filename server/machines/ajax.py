from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework import status
from django.db.models import Q, Prefetch

from .models import Machine
from people.models import Qualification

AUTOCOMPLETE_RESULT_LIMIT = 20


class HasViewMachinePermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.has_perm("machines.view_machine"))


def get_machines(request, term):
    if not term:
        return Machine.objects.none()
    return Machine.objects.filter(Q(name__icontains=term) | Q(hostname__icontains=term))


class MachineAutocompleteView(APIView):
    queryset = Machine.objects.all()
    permission_classes = [HasViewMachinePermission]

    def get(self, request, format=None):
        machines = get_machines(request, request.GET.get("term", None))[
            :AUTOCOMPLETE_RESULT_LIMIT
        ]
        return Response(
            [{"value": machine.id, "label": machine.name} for machine in machines],
            status=status.HTTP_200_OK,
        )


class QualifyableMachineAutocompleteView(APIView):
    queryset = Machine.objects.all()
    permission_classes = [HasViewMachinePermission]

    def get(self, request, person=None):
        machines = get_machines(request, request.GET.get("term", None))
        machines = machines.filter(needs_qualification=True, state=Machine.MachineStatus.ACTIVE)
        machines = machines.exclude(qualified_people__person__id=person)
        machines = machines.prefetch_related(
            Prefetch(
                "qualified_people",
                queryset=Qualification.objects.filter(is_instructor=True)
                .select_related("person")
                .order_by("person__name"),
                to_attr="prefetched_instructors",
            )
        )[:AUTOCOMPLETE_RESULT_LIMIT]
        returned = []
        for machine in machines:
            instructors = [
                {"value": qualification.person.pk, "label": qualification.person.name}
                for qualification in machine.prefetched_instructors
            ]
            returned.append(
                {
                    "value": machine.id,
                    "label": f"{machine.name} ({machine.hostname})",
                    "instructors": instructors,
                }
            )
        return Response(returned, status=status.HTTP_200_OK)