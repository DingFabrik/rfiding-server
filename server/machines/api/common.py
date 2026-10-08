import datetime
import hmac
import logging

from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.db.models import Q
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from machines.models import Machine, PERMISSION_LEVELS
from machines.serializers import MachineConfigSerializer
from holidays.utils import is_today_holiday
from tokens.models import Token, UnknownToken, BlacklistedToken
from access_log.tasks import save_access_log
from access_log.models import (
    LOG_TYPE_DISABLED,
    LOG_TYPE_ENABLED,
    LOG_TYPE_UNSUCCESSFUL,
    UnsuccessfulReason,
)
from people.models import Person, Qualification
from space.models import SpaceState

logger = logging.getLogger(__name__)


def formatted_mac(mac_address):
    if mac_address is None:
        return None
    if not isinstance(mac_address, str):
        raise ValidationError("mac_address must be a string")
    if ":" not in mac_address:
        return ":".join(
            mac_address[i : i + 2].lower() for i in range(0, len(mac_address), 2)
        )
    return mac_address.lower()


class BaseAPIView(APIView):
    required_get_parameters = None
    required_post_parameters = None
    required_delete_parameters = None

    def get_machine(self, mac_address):
        if mac_address is None:
            raise NotFound("Machine does not exist")
        try:
            return Machine.objects.get(
                ~Q(state=Machine.MachineStatus.INACTIVE),
                mac_address=mac_address
            )
        except Machine.DoesNotExist:
            raise NotFound("Machine does not exist") from None
        except Machine.MultipleObjectsReturned:
            raise NotFound("Machine does not exist") from None

    def initial(self, request, *args, **kwargs):
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
        super().initial(request, *args, **kwargs)


class MachineApiKeyPermission(permissions.BasePermission):
    """Requires a matching Api-Key header when the machine has an api_key set.

    If the machine has no api_key configured, unauthenticated access is
    allowed unless ENFORCE_API_KEYS is set.
    """

    machine_param = "mac_address"

    def has_permission(self, request, view):
        mac_address = formatted_mac(
            request.GET.get(
                self.machine_param, request.data.get(self.machine_param, None)
            )
        )
        view.machine = view.get_machine(mac_address)
        api_key = view.machine.api_key
        if api_key:
            provided_key = request.headers.get("Api-Key")
            return provided_key is not None and hmac.compare_digest(
                provided_key, api_key
            )
        return not getattr(settings, "ENFORCE_API_KEYS", False)


class AccessFailureMixin:
    """Carries why an access check failed, so the caller can log it."""

    def __init__(self, detail, reason, token_id=None):
        super().__init__(detail)
        self.reason = reason
        self.token_id = token_id


class AccessDenied(AccessFailureMixin, PermissionDenied):
    pass


class AccessNotFound(AccessFailureMixin, NotFound):
    pass


def check_space_open(permission_level, token_id):
    if permission_level == PERMISSION_LEVELS[0][0]:
        space_state = SpaceState.objects.first()
        if space_state is not None and not space_state.is_open:
            raise AccessDenied(
                "Space is closed", UnsuccessfulReason.SPACE_CLOSED, token_id
            )


def truncate_token_id(token_id):
    """Cut a token ID read during an access check to TOKEN_ID_MAX_LENGTH.

    Readers report some tag types (e.g. MIFARE Ultralight's 7-byte UIDs) with a
    longer ID than legacy devices do. Truncating here makes all devices agree on
    one ID per tag. Stored serials are never truncated - only the ID a machine
    sends is, before it's looked up and before it's saved as an unknown token.
    """
    max_length = getattr(settings, "TOKEN_ID_MAX_LENGTH", None)
    if max_length:
        return token_id[:max_length]
    return token_id


def check_access(machine, tokenID, compartmentID=None):
    tokenID = truncate_token_id(tokenID)
    checked_machine = machine
    if compartmentID is not None:
        try:
            checked_machine = machine.children.get(compartment_id=compartmentID)
        except Machine.DoesNotExist:
            raise AccessNotFound(
                "Machine does not exist", UnsuccessfulReason.UNKNOWN_COMPARTMENT
            ) from None
    if checked_machine.type == "lock_group":
        raise AccessDenied("Machine is a lock group", UnsuccessfulReason.LOCK_GROUP)
    if not checked_machine.allowed_on_holidays and is_today_holiday():
        raise AccessDenied(
            "Machine is restricted on holidays", UnsuccessfulReason.HOLIDAY
        )
    end_time = Machine.get_valid_end_time_for_machine(checked_machine.id)
    if end_time is None:
        raise AccessDenied("Machine is restricted", UnsuccessfulReason.OUTSIDE_HOURS)

    try:
        token = Token.objects.values("id", "person__id").get(
            serial=tokenID, archived=None, is_active=True, person__is_active=True
        )
    except Token.DoesNotExist:
        serial_max_length = Token._meta.get_field("serial").max_length
        if (
            len(tokenID) <= serial_max_length
            and not BlacklistedToken.objects.filter(serial=tokenID).exists()
        ):
            UnknownToken.objects.get_or_create(serial=tokenID, machine_id=checked_machine.id)
        # The token may exist but be archived/deactivated or belong to an inactive person.
        # Either way the caller gets the same 403 "No Access!" as for a known token
        # without access, so the API can't be used to probe which serials exist.
        # The precise reason is still written to the access log.
        inactive_token_id = (
            Token.objects.filter(serial=tokenID).values_list("id", flat=True).first()
        )
        if inactive_token_id is not None:
            raise AccessDenied(
                "No Access!", UnsuccessfulReason.INACTIVE_TOKEN, inactive_token_id
            ) from None
        raise AccessDenied("No Access!", UnsuccessfulReason.UNKNOWN_TOKEN) from None

    def log_enabled():
        save_access_log.delay(
            machine.id, token["id"], LOG_TYPE_ENABLED, timestamp=timezone.now()
        )

    if checked_machine.needs_qualification:
        person = token["person__id"]
        qualifications = Qualification.objects.filter(
                machine=checked_machine.id, person=person
            )
        if checked_machine.state == Machine.MachineStatus.MAINTENANCE:
            qualifications = qualifications.filter(is_maintainer=True)
        qualification = (
            qualifications
            .order_by()
            .first()
        )
        is_maintainer_bypass = False
        if qualification is None:
            denied_reason = UnsuccessfulReason.NOT_QUALIFIED
        elif qualification.permission_level == PERMISSION_LEVELS[2][0]:
            denied_reason = UnsuccessfulReason.QUALIFICATION_BLOCKED
        elif qualification.expired is not None:
            denied_reason = UnsuccessfulReason.QUALIFICATION_EXPIRED
        else:
            denied_reason = None
        if denied_reason is not None:
            if checked_machine.state == Machine.MachineStatus.MAINTENANCE:
                is_system_maintainer = Person.objects.filter(
                    id=person,
                    is_system_maintainer=True
                ).exists()
                if not is_system_maintainer:
                    raise AccessDenied(
                        "Machine in maintenance",
                        UnsuccessfulReason.MAINTENANCE,
                        token["id"],
                    )
                is_maintainer_bypass = True
            else:
                raise AccessDenied("No Access!", denied_reason, token["id"])

        if not is_maintainer_bypass:
            check_space_open(qualification.permission_level, token["id"])
            with transaction.atomic():
                qualification.mark_used()
                transaction.on_commit(log_enabled)
        else:
            log_enabled()
    else:
        if checked_machine.permission_level == PERMISSION_LEVELS[2][0]:
            raise AccessDenied(
                "No Access!", UnsuccessfulReason.MACHINE_BLOCKED, token["id"]
            )
        check_space_open(checked_machine.permission_level, token["id"])
        log_enabled()

    now = datetime.datetime.now()
    return {
        "access": 1,
        "workingtime": int(
            (datetime.datetime.combine(now, end_time) - now).total_seconds()
        ),
        "end_time": datetime.datetime.combine(now, end_time).strftime("%H:%M:%S"),
    }


def run_access_check(machine, tokenID, compartmentID=None):
    """Runs check_access and returns (http_status, data).

    Denied attempts are written to the access log together with the reason.
    Shared by the HTTP API and the ESPHome native API.
    """
    was_successful = False
    reason = UnsuccessfulReason.INTERNAL_ERROR
    token_id = None
    try:
        return_data = check_access(machine, tokenID, compartmentID)
        was_successful = True
        return status.HTTP_200_OK, return_data
    except PermissionDenied as e:
        reason = getattr(e, "reason", reason)
        token_id = getattr(e, "token_id", None)
        return status.HTTP_403_FORBIDDEN, {"error": str(e), "access": 0}
    except NotFound as e:
        reason = getattr(e, "reason", reason)
        token_id = getattr(e, "token_id", None)
        return status.HTTP_404_NOT_FOUND, {"error": str(e), "access": 0}
    except Exception:
        logger.exception("Unexpected error checking access for machine %s", machine.pk)
        return status.HTTP_403_FORBIDDEN, {"error": "Internal error", "access": 0}
    finally:
        if not was_successful:
            save_access_log.delay(
                machine.id,
                token_id,
                LOG_TYPE_UNSUCCESSFUL,
                timestamp=timezone.now(),
                reason=reason,
            )


def check_access_response(machine, tokenID, compartmentID=None):
    """Runs check_access and turns the outcome into an API response."""
    status_code, data = run_access_check(machine, tokenID, compartmentID)
    return Response(data, status=status_code)


def machine_config(machine):
    """The configuration a machine loads from the server."""
    config = {
        "runtimer": machine.runtimer,
        "minPower": machine.min_power,
        "display_time_countdown": machine.display_time_countdown,
        "display_power_consumption": machine.display_power_consumption,
        "link_relays": machine.link_relays,
    }
    if machine.type == Machine.MachineType.LOCK_GROUP:
        config["compartments"] = machine.children.exclude(
            Q(compartment_id__isnull=True) | Q(compartment_id="")
        )
    return MachineConfigSerializer(config).data


def update_reported_machine_info(machine, data):
    """Stores the ip address and firmware version a machine reports about itself."""
    changed_fields = []
    for field in ("ip_address", "firmware_version"):
        if field in data and data[field] and getattr(machine, field) != data[field]:
            setattr(machine, field, data[field])
            changed_fields.append(field)
    if changed_fields:
        machine.save()
    return changed_fields


def log_machine_disabled(machine, compartmentID=None):
    """Logs that a machine (or one of its compartments) was locked again."""
    if compartmentID is not None:
        try:
            machine = machine.children.get(compartment_id=compartmentID)
        except Machine.DoesNotExist:
            raise NotFound("Machine does not exist") from None
    save_access_log.delay(machine.id, None, LOG_TYPE_DISABLED, timestamp=timezone.now())
