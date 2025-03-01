from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import status, permissions
from django.conf import settings

from .common import formatted_mac, BaseAPIView
from access_log.models import LOG_TYPE_BOOTED, LOG_TYPE_DISABLED, LOG_TYPE_UNSUCCESSFUL
from access_log.tasks import save_access_log
from machines.serializers import MachineConfigSerializer
from machines.socket_helper import send_socket_action
from machines.api.common import check_access
from machines.models import Machine, MachineRegistrationRequest

ENFORCE_API_KEYS = settings.ENFORCE_API_KEYS if hasattr(settings, "ENFORCE_API_KEYS") else False

class MachineApiKeyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        mac_address = formatted_mac(request.GET.get("mac_address", request.POST.get("mac_address", None)))
        view.machine = view.get_machine(mac_address)
        if view.machine["api_key"] is not None:
            return request.META.get("api-key", None) == view.machine["api_key"]
        return True

class MachineRegisterView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    required_post_parameters = ["mac_address", "hostname"]

    def post(self, request, format=None):
        mac_address = formatted_mac(request.data.get("mac_address", None))
        try:
            self.get_machine(mac_address)
            return Response(
                {
                    "registered": True,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except NotFound:
            if not MachineRegistrationRequest.objects.filter(mac_address=mac_address).exists():
                ip_address = request.data.get("ip_address", request.META.get("REMOTE_ADDR", None))
                hostname = request.data.get("hostname", None)
                MachineRegistrationRequest.objects.create(
                    mac_address=mac_address,
                    ip_address=ip_address,
                    hostname=hostname,
                )
            return Response(
                {
                    "registered": False,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        
class MachineConnectView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_get_parameters = ["mac_address"]

    def get(self, request, format=None):
        send_socket_action(self.machine.pk, "connect")

        return Response(
            {
                "connected": True,
            },
            status=status.HTTP_200_OK,
        )

class MachineConfigView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_get_parameters = ["mac_address"]
    required_post_parameters = ["mac_address"]

    def get(self, request, format=None):
        save_access_log.delay(self.machine.id, None, LOG_TYPE_BOOTED)
        return Response(
            MachineConfigSerializer({
                "runtimer": self.machine.runtimer,
                "minPower": self.machine.min_power,
            }).data,
            status=status.HTTP_200_OK,
        )
    
    def post(self, request, format=None):
        was_changed = False
        if "ip_address" in request.data and self.machine.ip_address != request.data["ip_address"]:
            self.machine.ip_address = request.data["ip_address"]
            was_changed = True
        if "firmware_version" in request.data and self.machine.firmware_version != request.data["firmware_version"]:
            self.machine.firmware_version = request.data["firmware_version"]
            was_changed = True
        if was_changed:
            self.machine.save()
        
        save_access_log.delay(self.machine.id, None, LOG_TYPE_BOOTED)
        return Response(
            MachineConfigSerializer({
                "runtimer": self.machine.runtimer,
                "minPower": self.machine.min_power,
                "display_time_countdown": self.machine.display_time_countdown,
                "display_power_consumption": self.machine.display_power_consumption,
                "link_relays": self.machine.link_relays,
            }).data,
            status=status.HTTP_200_OK,
        )
        
class CheckMachineAccessView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_get_parameters = ["mac_address", "tokenUid"]

    def get(self, request, format=None):
        tokenID = request.GET.get("tokenUid", None).lower()

        was_successful = False
        try:
            return_data = check_access(self.machine, tokenID)
            was_successful = True
            return Response(return_data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response({"error": str(e), "access": 0}, status=status.HTTP_403_FORBIDDEN)
        except NotFound as e:
            return Response({"error": str(e), "access": 0}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e), "access": 0}, status=status.HTTP_403_FORBIDDEN)
        finally:
            if not was_successful:
                save_access_log.delay(self.machine["id"], None, LOG_TYPE_UNSUCCESSFUL)

class DisableMachineAccessView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_get_parameters = ["mac_address", "tokenUid"]

    def get(self, request, format=None):
        save_access_log.delay(self.machine["id"], None, LOG_TYPE_DISABLED)
        return Response({})