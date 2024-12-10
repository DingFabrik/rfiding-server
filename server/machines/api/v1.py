import datetime
from people.models import PERMISSION_LEVELS
from rest_framework.response import Response
from rest_framework import status, permissions
from space.models import SpaceState

from .common import formatted_mac, BaseAPIView
from tokens.models import Token, UnknownToken, BlacklistedToken
from access_log.models import AccessLog, LOG_TYPE_BOOTED, LOG_TYPE_ENABLED


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

        end_time = machine.get_valid_end_time()
        if end_time is None:
            return Response(
                {"error": "Machine is restricted", "access": 0},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            token = Token.objects.select_related("person").get(serial=tokenID, archived=None, is_active=True, person__is_active=True)
        except Token.DoesNotExist:
            if not BlacklistedToken.objects.filter(serial=tokenID).exists():
                UnknownToken.objects.get_or_create(serial=tokenID, machine=machine)
            return Response(
                {"error": "Token does not exist", "access": 0},
                status=status.HTTP_404_NOT_FOUND,
            )

        if machine.needs_qualification:
            qualification = (
                token.person.qualifications.filter(machine=machine).order_by().first()
            )
            if qualification is None or qualification.permission_level == PERMISSION_LEVELS[2][0]:
                return Response(
                    {"error": "Person does not have access to machine", "access": 0},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if qualification.permission_level == PERMISSION_LEVELS[0][0]:
                space_state = SpaceState.objects.first()
                if space_state is not None and not space_state.is_open:
                    return Response(
                        {"error": "Space is closed", "access": 0},
                        status=status.HTTP_403_FORBIDDEN,
                    )
        AccessLog.objects.create(machine=machine, token=token, type=LOG_TYPE_ENABLED)
        now = datetime.datetime.now()
        return Response(
            {
                "access": 1,
                "workingtime": int(
                    (datetime.datetime.combine(now, end_time) - now).total_seconds()
                ),
            },
            status=status.HTTP_200_OK,
        )
