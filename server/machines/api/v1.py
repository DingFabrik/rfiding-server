from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import status, permissions

from .common import check_access, formatted_mac, BaseAPIView
from access_log.models import AccessLog, LOG_TYPE_BOOTED

class MachineConfigView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    required_get_parameters = ["machine"]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get("machine", None))
        machine = self.get_machine(mac_address)

        AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
        return Response(
            {
                "runtimer": machine.runtimer,
                "minPower": machine.min_power,
                "controlParameter": machine.control_parameter,
            },
            status=status.HTTP_200_OK,
        )


class CheckMachineAccessView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    required_get_parameters = ["machine", "tokenUid"]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get("machine", None))
        tokenID = request.GET.get("tokenUid", None).lower()

        machine = self.get_machine(mac_address)

        try:
            return_data = check_access(machine, tokenID)
            return Response(return_data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response({"error": str(e), "access": 0}, status=status.HTTP_403_FORBIDDEN)
        except NotFound as e:
            return Response({"error": str(e), "access": 0}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e), "access": 0}, status=status.HTTP_403_FORBIDDEN)
