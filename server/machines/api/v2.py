from rest_framework.response import Response
from rest_framework import status, permissions

from .common import formatted_mac, BaseAPIView
from access_log.models import AccessLog, LOG_TYPE_REGISTERED, LOG_TYPE_BOOTED
from machines.serializers import MachineConfigSerializer

class MachineRegisterView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    required_post_parameters = ["machine"]

    def post(self, request, format=None):
        mac_address = formatted_mac(request.POST.get("machine", None))
        machine = self.get_machine(mac_address)

        AccessLog.objects.create(machine=machine, type=LOG_TYPE_REGISTERED)
        return Response(
            {
                "runtimer": machine.runtimer,
                "minPower": machine.min_power,
                "controlParameter": machine.control_parameter,
            },
            status=status.HTTP_200_OK,
        )

class MachineConfigView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    required_get_parameters = ["machine"]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get("machine", None))
        machine = self.get_machine(mac_address)

        AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
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