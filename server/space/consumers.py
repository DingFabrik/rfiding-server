import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings as SETTINGS
import logging

from .common import aupdate_space_state, aget_current_space_state

logger = logging.getLogger(__name__)


class SpaceStateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("space_state", self.channel_name)
        await self.accept()

        await self.send(
            json.dumps({"state": (await aget_current_space_state()).is_open})
        )
        logger.debug("Websocket client connected")

    async def disconnect(self, code):
        await self.channel_layer.group_discard("space_state", self.channel_name)
        logger.debug("websocket client disconnected")
        return await super().disconnect(code)

    async def receive(self, text_data=None, bytes_data=None):
        logger.debug("Received websocket data:", text_data)
        if (
            text_data is None
            or text_data == ""
            or text_data.lower() == "ping"
            or text_data.lower() == "pong"
        ):
            return
        json_data = json.loads(text_data)

        if json_data["method"] == "change_state":
            if (
                "secret" not in json_data
                or json_data["secret"] != SETTINGS.SPACE_STATE_SECRET
            ):
                await self.send(json.dumps({"error": "invalid secret"}))
                await self.close()
                return
            new_state = json_data["state"]
            await aupdate_space_state(new_state)
        else:
            await self.send(json.dumps({"error": "invalid method"}))

    async def space_state(self, event):
        logger.debug("Sending new state through websocket")
        await self.send(json.dumps({"state": event["state"]}))
