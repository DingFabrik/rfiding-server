import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings as SETTINGS

from .models import SpaceState
from .common import aupdate_space_state, aget_current_space_state

channel_layer = get_channel_layer()

class SpaceStateConsumer(AsyncJsonWebsocketConsumer):
    
    async def connect(self):
        await channel_layer.group_add("space_state", self.channel_name)
        await self.accept()
        
        await self.send(json.dumps({"state": str((await aget_current_space_state()).is_open)}))
    
    async def disconnect(self, code):
        channel_layer.group_discard("space_state", self.channel_name)
        return super().disconnect(code)
    
    async def receive(self, text_data=None, bytes_data=None):
        json_data = json.loads(text_data)
        
        if json_data["method"] == "change_state":
            if "secret" not in json_data or json_data["secret"] != SETTINGS.SPACE_STATE_SECRET:
                await self.send(json.dumps({"error": "invalid secret"}))
                await self.close()
                return
            new_state = json_data["state"]
            await aupdate_space_state(new_state)
        await self.send(json.dumps({"error": "invalid method"}))
            
    async def space_state(self, event):
        await self.send(json.dumps({"state": event["state"]}))