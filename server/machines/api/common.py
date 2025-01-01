import datetime
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework import status

from machines.models import Machine
from tokens.models import Token, UnknownToken, BlacklistedToken
from access_log.models import AccessLog, LOG_TYPE_ENABLED
from people.models import PERMISSION_LEVELS
from space.models import SpaceState

def formatted_mac(mac_address):
    if mac_address is None:
        return None
    if ":" not in mac_address:
        return ":".join(
            mac_address[i : i + 2].lower() for i in range(0, len(mac_address), 2)
        )
    return mac_address


class BaseAPIView(APIView):
    required_get_parameters = None
    required_post_parameters = None
    required_delete_parameters = None


    def get_machine(self, mac_address):
        try:
            return Machine.objects.get(mac_address__iexact=mac_address, is_active=True)
        except Machine.DoesNotExist:
            raise NotFound("Machine does not exist") from None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method.lower() == "get" and self.required_get_parameters:
            for param in self.required_get_parameters:
                if request.GET.get(param, None) is None:
                    raise ValidationError(f"Missing parameter {param}")
        if request.method.lower() == "post" and self.required_post_parameters:
            for param in self.required_post_parameters:
                if request.POST.get(param, None) is None:
                    raise ValidationError(f"Missing parameter {param}")
        if request.method.lower() == "delete" and self.required_delete_parameters:
            for param in self.required_delete_parameters:
                if request.GET.get(param, None) is None:
                    raise ValidationError(f"Missing parameter {param}")


def check_access(machine, tokenID):
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
    return {
            "access": 1,
            "workingtime": int(
                (datetime.datetime.combine(now, end_time) - now).total_seconds()
            ),
        }