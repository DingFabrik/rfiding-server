from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import Machine, MachineConfig

class MachineAutocompleteView(APIView):
    queryset = Machine.objects.all()
    def get (self, request, format=None):
        machines = Machine.objects.filter(name__icontains=request.GET.get('term', None))
        return Response([{'value': machine.id, 'label': machine.name} for machine in machines], status=status.HTTP_200_OK)
    
class QualifyableMachineAutocompleteView(APIView):
    queryset = Machine.objects.all()
    def get (self, request, person=None):
        machines = Machine.objects.filter(name__icontains=request.GET.get('term', None))
        machines = machines.exclude(qualified_people__person__id=person)
        return Response([{'value': machine.id, 'label': f"{machine.name} ({machine.hostname})"} for machine in machines], status=status.HTTP_200_OK)
    
class InstructorMachineAutocompleteView(APIView):
    queryset = Machine.objects.all()
    def get (self, request, person=None):
        machines = Machine.objects.filter(name__icontains=request.GET.get('term', None))
        machines = machines.exclude(instructors__person__id=person)
        return Response([{'value': machine.id, 'label': f"{machine.name} ({machine.hostname})"} for machine in machines], status=status.HTTP_200_OK)