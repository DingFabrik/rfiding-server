import logging

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import status

from .common import check_access, BaseAPIView, MachineApiKeyPermission
from access_log.models import LOG_TYPE_BOOTED
from access_log.tasks import save_access_log

logger = logging.getLogger(__name__)


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

        try:
            return_data = check_access(self.machine, tokenID)
            return Response(return_data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response(
                {"error": str(e), "access": 0}, status=status.HTTP_403_FORBIDDEN
            )
        except NotFound as e:
            return Response(
                {"error": str(e), "access": 0}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            logger.exception(
                "Unexpected error checking access for machine %s", self.machine.pk
            )
            return Response(
                {"error": "Internal error", "access": 0},
                status=status.HTTP_403_FORBIDDEN,
            )
