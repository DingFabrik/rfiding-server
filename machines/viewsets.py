from typing import Any
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied

from machines.models import AccessLogEntry, Machine
from machines.serializers import AccessGrantedSerializer, MachineConfigSerializer
from tokens.models import Token

class RetrieveMachineConfigAPIView(RetrieveAPIView):
    queryset = Machine.objects.all()

    def get(self, request, *args, **kwargs):
        machine = get_object_or_404(Machine, mac_address=request.GET["machine"])
        serializer = MachineConfigSerializer(machine)
        return Response(serializer.data)
    
def fail(machine, person, reason):
    log = AccessLogEntry()
    log.was_allowed = False
    log.machine = machine
    log.person = person
    log.save()
    raise PermissionDenied()

class CheckMachineAccess(APIView):
    def get(self, request, *args, **kwargs):
        machine = get_object_or_404(Machine, mac_address=request.GET["machine"])
        token = get_object_or_404(Token, serial=request.GET["tokenUid"])
        try:
            return Token.objects.get(serial=request.GET["tokenUid"])
        except Token.DoesNotExist:
            raise Http404(
                "No %s matches the given query." % queryset.model._meta.object_name
            )
        if not machine.can_be_used():
            fail(machine, token.owner, "Machine can not be used")
        if not token.is_active:
            fail(machine, token.owner, "Token is not active")
        if token.owner.qualifications.filter(machine__pk=machine.pk).count() == 0:
            fail(machine, token.owner, "User is not qualified to use machine")
        
        log = AccessLogEntry()
        log.was_allowed = False
        log.machine = machine
        log.person = token.owner
        log.save()

        serializer = AccessGrantedSerializer({
            "access": 1,
            "workingTime": 100
        })
        return Response(serializer.data)