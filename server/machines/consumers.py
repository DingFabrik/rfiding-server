from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging
from django.template.loader import render_to_string
import asyncio
import datetime
import re
from asgiref.sync import sync_to_async

from .management.commands.machine_manager import ConnectionManager
from .models import Machine

logger = logging.getLogger(__name__)


class MachineStateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated and await sync_to_async(user.has_perm)("machines.view_machine_state"):
            return await self.close()
        self.scope["can_send_commands"] = await sync_to_async(user.has_perm)("machines.send_machine_commands")
        await self.accept()

        mac_address = self.scope["url_route"]["kwargs"]["mac_address"]
        machine = await Machine.objects.aget(
            mac_address__iexact=mac_address, is_active=True
        )

        self.manager = ConnectionManager(machine)
        self.manager.on_state_change = self.state_update
        await self.manager.connect()

    async def disconnect(self, code):
        logger.debug("websocket client disconnected")
        if self.manager is not None:
            await self.manager.disconnect()
        return await super().disconnect(code)

    async def receive_json(self, content, **kwargs):
        logger.debug("Received websocket data:", content)
        if "command" in content:
            if not self.scope["can_send_commands"]:
                return
            self.manager.send_command(content["command"])

    async def state_update(self, state):
        html = render_to_string(
            "machine_status_partial.html",
            {
                "status": state["state"],
            },
        )
        await self.send(html)

def parse_log_message(message):
    try:
        decoded = message.decode("utf-8")
        decoded = re.sub(r"\x1b\[[0-9;]*m", "", decoded)
        return decoded
    except UnicodeDecodeError:
        return message.hex()

class MachineLogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()

        mac_address = self.scope["url_route"]["kwargs"]["mac_address"]
        machine = await Machine.objects.aget(
            mac_address__iexact=mac_address, is_active=True
        )

        self.manager = ConnectionManager(machine)
        await self.manager.connect()

        def log_update(log):
            asyncio.ensure_future(self.state_update(log))

        self.manager.client.subscribe_logs(log_update, 5, True)

    async def disconnect(self, code):
        logger.debug("websocket client disconnected")
        if self.manager is not None:
            await self.manager.disconnect()
        return await super().disconnect(code)

    async def state_update(self, log):
        html = render_to_string(
            "machine_log_partial.html",
            {
                "timestamp": datetime.datetime.now(),
                "level": log.level,
                "message": parse_log_message(log.message),
            },
        )
        await self.send(html)
