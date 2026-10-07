import ipaddress

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status, permissions
from rest_framework.throttling import ScopedRateThrottle

from .common import formatted_mac, BaseAPIView, MachineApiKeyPermission
from access_log.models import LOG_TYPE_BOOTED
from access_log.tasks import save_access_log
from machines.esphome import bridge
from machines.esphome.protocol import COMMANDS
from machines.api.common import (
    check_access_response,
    log_machine_disabled,
    machine_config,
    update_reported_machine_info,
)
from machines.models import MachineRegistrationRequest


def is_ip_address(value):
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


class MachineRegisterView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    # Unauthenticated, so limit how fast one client can create registration requests.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "machine_register"
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
            if not MachineRegistrationRequest.objects.filter(
                mac_address=mac_address
            ).exists():
                ip_address = request.data.get("ip_address", None)
                if not is_ip_address(ip_address):
                    ip_address = request.META.get("REMOTE_ADDR", None)
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
        bridge.notify_machine_changed(self.machine.pk)

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
        save_access_log.delay(self.machine.id, None, LOG_TYPE_BOOTED, timestamp=timezone.now())
        return Response(machine_config(self.machine), status=status.HTTP_200_OK)

    def post(self, request, format=None):
        update_reported_machine_info(self.machine, request.data)
        save_access_log.delay(self.machine.id, None, LOG_TYPE_BOOTED, timestamp=timezone.now())
        return Response(machine_config(self.machine), status=status.HTTP_200_OK)


class CheckMachineAccessView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_get_parameters = ["mac_address", "tokenUid"]

    def get(self, request, format=None):
        tokenID = request.GET.get("tokenUid", None).lower()
        compartmentID = request.GET.get("compartmentID", None)

        return check_access_response(self.machine, tokenID, compartmentID)

class MachineDisableView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_get_parameters = ["mac_address", "tokenUid"]

    def get(self, request, format=None):
        log_machine_disabled(self.machine, request.GET.get("compartmentID", None))
        return Response({})

class MachineControlView(BaseAPIView):
    permission_classes = [MachineApiKeyPermission]
    required_post_parameters = ["mac_address", "action", "control_key"]

    def post(self, request, format=None):
        if not self.machine.has_api:
            return Response(
                {"error": "Machine does not have API enabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not self.machine.control_keys.filter(key=request.data["control_key"]).exists():
            return Response(
                {"error": "Invalid control key"},
                status=status.HTTP_403_FORBIDDEN,
            )
        action = request.data.get("action", None)
        if action not in COMMANDS:
            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bridge.send_command(self.machine.pk, action)
        except bridge.ManagerUnavailable as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except bridge.CommandFailed as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({}, status=status.HTTP_200_OK)