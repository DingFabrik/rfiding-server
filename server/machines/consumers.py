from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging
from django.template.loader import render_to_string
import asyncio
import datetime
import re

from .management.commands.machine_manager import ConnectionManager
from .models import Machine

logger = logging.getLogger(__name__)


class MachineStateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
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
        print("disconnecting", self.manager)
        if self.manager is not None:
            await self.manager.disconnect()
        return await super().disconnect(code)

    async def receive(self, text_data=None, bytes_data=None):
        logger.debug("Received websocket data:", text_data)

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
        print(log)
        html = render_to_string(
            "machine_log_partial.html",
            {
                "timestamp": datetime.datetime.now(),
                "level": log.level,
                "message": parse_log_message(log.message),
            },
        )
        await self.send(html)
