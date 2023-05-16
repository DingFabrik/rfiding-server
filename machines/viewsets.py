from typing import Any
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.response import Response

from machines.models import Machine
from machines.serializers import MachineConfigSerializer

class RetrieveMachineConfigAPIView(RetrieveAPIView):
    queryset = Machine.objects.all()

    def get(self, request, *args, **kwargs):
        machine = get_object_or_404(Machine, pk=request.GET["pk"])
        serializer = MachineConfigSerializer(machine)
        return Response(serializer.data)