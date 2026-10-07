import logging

from django.db import close_old_connections
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound

from access_log.models import LOG_TYPE_BOOTED
from access_log.tasks import save_access_log
from machines.api.common import (
    log_machine_disabled,
    machine_config,
    run_access_check,
    update_reported_machine_info,
)
from machines.models import Machine

from . import protocol

logger = logging.getLogger(__name__)


class RequestError(Exception):
    pass


def _optional(data, key):
    value = data.get(key)
    return value if value else None


def check_access(machine, data):
    token = _optional(data, "token")
    if token is None:
        raise RequestError("Missing token")
    status_code, result = run_access_check(
        machine, token.lower(), _optional(data, "compartment")
    )
    result = dict(result)
    result["access"] = status_code == status.HTTP_200_OK
    return result


def config(machine, data):
    update_reported_machine_info(machine, data)
    save_access_log.delay(machine.id, None, LOG_TYPE_BOOTED, timestamp=timezone.now())
    return machine_config(machine)


def disabled(machine, data):
    try:
        log_machine_disabled(machine, _optional(data, "compartment"))
    except NotFound as e:
        raise RequestError(str(e)) from None
    return {}


HANDLERS = {
    protocol.REQUEST_CHECK_ACCESS: check_access,
    protocol.REQUEST_CONFIG: config,
    protocol.REQUEST_DISABLED: disabled,
}


def handle_request(machine_pk, service, data):
    """Runs the handler for a device request and returns its JSON response."""
    handler = HANDLERS.get(service)
    if handler is None:
        raise RequestError(f"Unknown request {service}")
    # This runs in a long-lived process: drop connections the database closed.
    close_old_connections()
    try:
        try:
            machine = Machine.objects.exclude(
                state=Machine.MachineStatus.INACTIVE
            ).get(pk=machine_pk)
        except Machine.DoesNotExist:
            raise RequestError("Machine does not exist") from None
        return handler(machine, data)
    finally:
        close_old_connections()
