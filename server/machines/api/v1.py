from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from .common import check_access_response, BaseAPIView, MachineApiKeyPermission
from access_log.models import LOG_TYPE_BOOTED
from access_log.tasks import save_access_log


class V1MachineApiKeyPermission(MachineApiKeyPermission):
    machine_param = "machine"


class MachineConfigView(BaseAPIView):
    permission_classes = [V1MachineApiKeyPermission]
    required_get_parameters = ["machine"]

    def get(self, request, format=None):
        save_access_log.delay(self.machine.id, None, LOG_TYPE_BOOTED, timestamp=timezone.now())
        return Response(
            {
                "runtimer": self.machine.runtimer.seconds * 1000 + self.machine.runtimer.microseconds // 1000,
                "minPower": self.machine.min_power,
                "controlParameter": self.machine.control_parameter if self.machine.control_parameter else "",
            },
            status=status.HTTP_200_OK,
        )


class CheckMachineAccessView(BaseAPIView):
    permission_classes = [V1MachineApiKeyPermission]
    required_get_parameters = ["machine", "tokenUid"]

    def get(self, request, format=None):
        tokenID = request.GET.get("tokenUid", None).lower()

        return check_access_response(self.machine, tokenID)
