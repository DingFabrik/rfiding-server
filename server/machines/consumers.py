import asyncio
import datetime
import logging

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.template.loader import render_to_string

from .api.common import formatted_mac
from .esphome import bridge, protocol
from .models import Machine

logger = logging.getLogger(__name__)


async def get_machine(scope):
    mac_address = formatted_mac(scope["url_route"]["kwargs"]["mac_address"])
    try:
        return await Machine.objects.exclude(
            state=Machine.MachineStatus.INACTIVE
        ).aget(mac_address=mac_address)
    except (Machine.DoesNotExist, Machine.MultipleObjectsReturned):
        return None


async def can_view_state(user):
    return user.is_authenticated and await sync_to_async(user.has_perm)(
        "machines.view_machine_state"
    )


class MachineStateConsumer(AsyncJsonWebsocketConsumer):
    """Shows a machine's live state; the machine manager pushes changes."""

    machine = None
    group = None

    async def connect(self):
        user = self.scope["user"]
        if not await can_view_state(user):
            return await self.close()
        self.machine = await get_machine(self.scope)
        if self.machine is None:
            return await self.close()
        self.can_send_commands = await sync_to_async(user.has_perm)(
            "machines.send_machine_commands"
        )
        self.group = protocol.machine_group(self.machine.pk)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_status(await bridge.aget_status(self.machine.pk))

    async def disconnect(self, code):
        if self.group is not None:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        command = content.get("command")
        if command is None or not self.can_send_commands:
            return
        try:
            await bridge.asend_command(self.machine.pk, command)
        except (ValueError, bridge.ManagerUnavailable, bridge.CommandFailed) as e:
            logger.warning("Command %s for %s failed: %s", command, self.machine, e)
            status = await bridge.aget_status(self.machine.pk)
            await self.send_status(status, command_error=str(e))

    async def machine_state(self, event):
        await self.send_status(event["status"])

    async def send_status(self, status, command_error=None):
        await self.send(
            render_to_string(
                "machine_status_partial.html",
                {
                    "status": status.get("state"),
                    "verified": status.get("verified"),
                    "command_error": command_error,
                },
            )
        )


class MachineLogConsumer(AsyncJsonWebsocketConsumer):
    """Streams a machine's logs while the log window is open."""

    machine = None
    renew_task = None

    async def connect(self):
        if not await can_view_state(self.scope["user"]):
            logger.warning("Unauthorized websocket connection attempt")
            return await self.close()
        self.machine = await get_machine(self.scope)
        if self.machine is None:
            return await self.close()
        await self.accept()
        self.renew_task = asyncio.create_task(self.keep_subscribed())

    async def keep_subscribed(self):
        while True:
            await bridge.asubscribe_logs(self.machine.pk, self.channel_name)
            await asyncio.sleep(protocol.LOG_LEASE_RENEW_INTERVAL)

    async def disconnect(self, code):
        if self.renew_task is not None:
            self.renew_task.cancel()
        if self.machine is not None:
            await bridge.aunsubscribe_logs(self.machine.pk, self.channel_name)

    async def machine_log(self, event):
        await self.send(
            render_to_string(
                "machine_log_partial.html",
                {
                    "timestamp": datetime.datetime.now(),
                    "level": event["level"],
                    "message": event["message"],
                },
            )
        )
