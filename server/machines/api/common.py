import datetime
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied

from machines.models import Machine
from tokens.models import Token, UnknownToken, BlacklistedToken
from access_log.tasks import save_access_log
from access_log.models import LOG_TYPE_ENABLED
from people.models import PERMISSION_LEVELS, Qualification
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
            return Machine.objects.values("id", "needs_qualification", "api_key", "runtimer", "min_power", "control_parameter", "display_time_countdown", "display_power_consumption", "link_relays").get(
                mac_address__iexact=mac_address, is_active=True
            )
        except Machine.DoesNotExist:
            raise NotFound("Machine does not exist") from None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method.lower() == "get" and self.required_get_parameters:
            for param in self.required_get_parameters:
                if request.GET.get(param, None) is None:
                    raise ValidationError(f"Missing {param}")
        if request.method.lower() == "post" and self.required_post_parameters:
            for param in self.required_post_parameters:
                if request.data.get(param, None) is None:
                    raise ValidationError(f"Missing {param}")
        if request.method.lower() == "delete" and self.required_delete_parameters:
            for param in self.required_delete_parameters:
                if request.GET.get(param, None) is None:
                    raise ValidationError(f"Missing {param}")


def check_access(machine, tokenID):
    end_time = Machine.get_valid_end_time_for_machine(machine["id"])
    if end_time is None:
        raise PermissionDenied("Machine is restricted")

    try:
        token = (
            Token.objects.select_related("person")
            .values("id", "person__id")
            .get(serial=tokenID, archived=None, is_active=True, person__is_active=True)
        )
    except Token.DoesNotExist:
        if not BlacklistedToken.objects.filter(serial=tokenID).exists():
            UnknownToken.objects.get_or_create(serial=tokenID, machine=machine["id"])
        raise NotFound("Invalid Token") from None

    if machine["needs_qualification"]:
        qualification = (
            Qualification.objects.filter(
                machine=machine["id"], person=token["person__id"]
            )
            .order_by()
            .first()
        )
        if (
            qualification is None
            or qualification.permission_level == PERMISSION_LEVELS[2][0]
        ):
            raise PermissionDenied("No Access!")

        if qualification.permission_level == PERMISSION_LEVELS[0][0]:
            space_state = SpaceState.objects.first()
            if space_state is not None and not space_state.is_open:
                raise PermissionDenied("Space is closed")
    save_access_log.delay(machine["id"], token["id"], LOG_TYPE_ENABLED)

    now = datetime.datetime.now()
    return {
        "access": 1,
        "workingtime": int(
            (datetime.datetime.combine(now, end_time) - now).total_seconds()
        ),
        "end_time": datetime.datetime.combine(now, end_time).strftime("%H:%M:%S"),
    }
