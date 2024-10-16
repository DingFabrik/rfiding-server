import datetime
from people.models import PERMISSION_LEVELS
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from space.models import SpaceState

from .common import formatted_mac
from machines.models import Machine
from tokens.models import Token, UnknownToken
from access_log.models import AccessLog, LOG_TYPE_BOOTED, LOG_TYPE_ENABLED


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

        if not machine.is_active:
            return Response(
                {"error": "Machine is restricted"}, status=status.HTTP_403_FORBIDDEN
            )

        log = AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
        log.save()
        return Response(
            {
                "runtimer": machine.runtimer,
                "minPower": machine.min_power,
                "controlParameter": machine.control_parameter,
            },
            status=status.HTTP_200_OK,
        )


class CheckMachineAccessView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get("machine", None))
        tokenID = request.GET.get("tokenUid", None)

        if mac_address is None or tokenID is None:
            return Response(
                {"error": "Missing parameters", "access": 0},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tokenID = tokenID.lower()


        try:
            machine = Machine.objects.get(mac_address=mac_address)
        except Machine.DoesNotExist:
            return Response(
                {"error": "Machine does not exist", "access": 0},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if not machine.is_active:
            return Response(
                {"error": "Machine is not active", "access": 0},
                status=status.HTTP_403_FORBIDDEN,
            )

        times = machine.times.all()
        end_time = None
        now = datetime.datetime.now()
        now_time = now.time()
        if len(times) == 0:
            end_time = datetime.time(23, 59, 59)
        else:
            weekday = now.weekday()
            for time in times:
                if (
                    weekday in time.weekdays
                    and time.start_time < now_time
                    and time.end_time > now_time
                ):
                    end_time = time.end_time
                    break

        if end_time is None:
            return Response(
                {"error": "Machine is restricted", "access": 0},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            token = Token.objects.select_related("person").get(serial=tokenID, archived=None)
        except Token.DoesNotExist:
            UnknownToken.objects.get_or_create(serial=tokenID, machine=machine)
            return Response(
                {"error": "Token does not exist", "access": 0},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not token.is_active or not token.person.is_active:
            return Response(
                {"error": "Token/Person is not active", "access": 0},
                status=status.HTTP_403_FORBIDDEN,
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
        return Response(
            {
                "access": 1,
                "workingtime": int(
                    (datetime.datetime.combine(now, end_time) - now).total_seconds()
                ),
            },
            status=status.HTTP_200_OK,
        )
