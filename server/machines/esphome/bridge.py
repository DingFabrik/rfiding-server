import asyncio
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from . import protocol

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5
STATUS_TIMEOUT = 2

DISCONNECTED_STATUS = {
    "connected": False,
    "verified": False,
    "state": "disconnected",
    "power": None,
    "error_message": None,
}


class ManagerUnavailable(Exception):
    """The machine manager is not running or did not answer in time."""


class CommandFailed(Exception):
    """The manager answered, but could not carry out the request."""


def is_enabled():
    return getattr(settings, "ENABLE_CLIENT_API", False)


def _layer():
    layer = get_channel_layer()
    if layer is None:
        raise ManagerUnavailable("No channel layer configured")
    return layer


async def arequest(message_type, timeout=REQUEST_TIMEOUT, **payload):
    """Sends a request to the manager and waits for its reply."""
    if not is_enabled():
        raise ManagerUnavailable("The client API is disabled")
    layer = _layer()
    reply_channel = await layer.new_channel()
    await layer.group_send(
        protocol.MANAGER_GROUP,
        {"type": message_type, "reply_channel": reply_channel, **payload},
    )
    try:
        reply = await asyncio.wait_for(layer.receive(reply_channel), timeout)
    except TimeoutError:
        raise ManagerUnavailable("The machine manager did not answer") from None
    if not reply.get("ok"):
        raise CommandFailed(reply.get("error") or "Unknown error")
    return reply


async def anotify(message_type, **payload):
    """Sends a message to the manager without waiting for an answer."""
    if not is_enabled():
        return
    try:
        await _layer().group_send(
            protocol.MANAGER_GROUP, {"type": message_type, **payload}
        )
    except Exception:
        logger.exception("Could not notify the machine manager")


async def asend_command(machine_pk, command):
    if command not in protocol.COMMANDS:
        raise ValueError(f"Unknown command {command}")
    return await arequest("machine.command", machine=machine_pk, command=command)


def send_command(machine_pk, command):
    """Runs a command on a machine. Raises ManagerUnavailable or CommandFailed."""
    return async_to_sync(asend_command)(machine_pk, command)


async def aget_status(machine_pk):
    """The live connection status of a machine, or DISCONNECTED_STATUS."""
    try:
        reply = await arequest(
            "machine.status", timeout=STATUS_TIMEOUT, machine=machine_pk
        )
    except (ManagerUnavailable, CommandFailed):
        return dict(DISCONNECTED_STATUS)
    return reply["status"]


def get_status(machine_pk):
    return async_to_sync(aget_status)(machine_pk)


async def aget_version():
    reply = await arequest("manager.version", timeout=STATUS_TIMEOUT)
    return reply["version"]


async def anotify_machine_changed(machine_pk):
    """Lets the manager (re)connect, disconnect or push config to a machine."""
    await anotify("machine.changed", machine=machine_pk)


def notify_machine_changed(machine_pk):
    if is_enabled():
        async_to_sync(anotify_machine_changed)(machine_pk)


async def asubscribe_logs(machine_pk, channel_name):
    await anotify("machine.logs.subscribe", machine=machine_pk, channel=channel_name)


async def aunsubscribe_logs(machine_pk, channel_name):
    await anotify(
        "machine.logs.unsubscribe", machine=machine_pk, channel=channel_name
    )
