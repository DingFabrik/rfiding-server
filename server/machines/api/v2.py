from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .common import formatted_mac
from machines.models import Machine
from access_log.models import AccessLog, LOG_TYPE_REGISTERED, LOG_TYPE_BOOTED
from machines.serializers import MachineConfigSerializer

class MachineRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        mac_address = formatted_mac(request.POST.get("machine", None))

        if mac_address is None:
            return Response(
                {"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            machine = Machine.objects.get(mac_address__iexact=mac_address)
        except Machine.DoesNotExist:
            return Response(
                {"error": "Machine does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        log = AccessLog.objects.create(machine=machine, type=LOG_TYPE_REGISTERED)
        log.save()
        return Response(
            {
                "runtimer": machine.runtimer,
                "minPower": machine.min_power,
                "controlParameter": machine.control_parameter,
            },
            status=status.HTTP_200_OK,
        )

class MachineConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get("machine", None))

        if mac_address is None:
            return Response(
                {"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            machine = Machine.objects.get(mac_address__iexact=mac_address)
        except Machine.DoesNotExist:
            return Response(
                {"error": "Machine does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        if not machine.is_active or not machine.is_now_valid_time():
            return Response(
                {"error": "Machine is restricted"}, status=status.HTTP_403_FORBIDDEN
            )

        log = AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
        log.save()
        return Response(
            MachineConfigSerializer({
                "runtimer": machine.runtimer,
                "minPower": machine.min_power,
                "controlParameter": machine.control_parameter,
                "accessControlModule": machine.access_control_module,
                "accessControlModuleSettings": machine.access_control_module_settings,
                "statusDisplayModule": machine.status_display_module,
                "statusDisplayModuleSettings": machine.status_display_module_settings,
                "actorModule": machine.actor_module,
                "actorModuleSettings": machine.actor_module_settings,
            }).data,
            status=status.HTTP_200_OK,
        )