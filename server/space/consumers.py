import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

from .common import aupdate_space_state, aget_current_space_state
from .secret import is_valid_space_secret

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
        try:
            json_data = json.loads(text_data)
        except ValueError:
            await self.send(json.dumps({"error": "invalid json"}))
            return
        if not isinstance(json_data, dict):
            await self.send(json.dumps({"error": "invalid message"}))
            return

        if json_data.get("method") == "change_state":
            if not is_valid_space_secret(json_data.get("secret")):
                await self.send(json.dumps({"error": "invalid secret"}))
                await self.close()
                return
            new_state = json_data.get("state")
            if new_state is None:
                await self.send(json.dumps({"error": "missing state"}))
                return
            await aupdate_space_state(new_state)
        else:
            await self.send(json.dumps({"error": "invalid method"}))

    async def space_state(self, event):
        logger.debug("Sending new state through websocket")
        await self.send(json.dumps({"state": event["state"]}))
