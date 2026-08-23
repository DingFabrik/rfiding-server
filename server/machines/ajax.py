from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework import status
from django.db.models import Q

from .models import Machine


class HasViewMachinePermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.has_perm("machines.view_machine"))


def get_machines(request, term):
    return Machine.objects.filter(Q(name__icontains=term) | Q(hostname__icontains=term))


class MachineAutocompleteView(APIView):
    queryset = Machine.objects.all()
    permission_classes = [HasViewMachinePermission]

    def get(self, request, format=None):
        machines = get_machines(request, request.GET.get("term", None))
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
        machines.select_related("instructors")
        returned = []
        for machine in machines:
            instructors = [
                {"value": instructor["person__pk"], "label": instructor["person__name"]}
                for instructor in machine.instructors.select_related("person")
                .order_by("person__name")
                .values("person__pk", "person__name")
                .all()
            ]
            returned.append(
                {
                    "value": machine.id,
                    "label": f"{machine.name} ({machine.hostname})",
                    "instructors": instructors,
                }
            )
        return Response(returned, status=status.HTTP_200_OK)