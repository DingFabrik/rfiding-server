from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging
from django.template.loader import render_to_string
import asyncio

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

        self.manager.client.subscribe_logs(log_update, 5)

    async def disconnect(self, code):
        logger.debug("websocket client disconnected")
        if self.manager is not None:
            await self.manager.disconnect()
        return await super().disconnect(code)

    async def state_update(self, log):
        html = render_to_string(
            "machine_log_partial.html",
            {
                "message": log.message.decode("utf-8"),
            },
        )
        print(html)
        await self.send(html)
