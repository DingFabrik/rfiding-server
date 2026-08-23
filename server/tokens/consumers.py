import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.template.loader import render_to_string
from asgiref.sync import sync_to_async

from .common import clear_unknown_tokens
from .models import UnknownToken

channel_layer = get_channel_layer()


class UnknownTokenConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated or not await sync_to_async(
            self.user.has_perm
        )("tokens.view_unknowntoken"):
            return await self.close()
        await channel_layer.group_add("unknown_tokens", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await channel_layer.group_discard("unknown_tokens", self.channel_name)
        return super().disconnect(code)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data["action"] == "clear":
            if not await sync_to_async(self.user.has_perm)("tokens.delete_unknowntoken"):
                return
            await sync_to_async(clear_unknown_tokens)()

    async def unknown_token_list_changed(self, event):
        tokens = [
            token
            async for token in UnknownToken.objects.prefetch_related("machine").all()
        ]
        if len(tokens) == 0:
            html = render_to_string("unknown_tokens_empty.html")
        else:
            html = render_to_string(
                "unknown_token_table.html",
                {
                    "tokens": tokens,
                    "is_partial": True,
                    "can_create_token": self.user.has_perm("tokens.add_token"),
                    "can_create_blacklistedtoken": self.user.has_perm(
                        "tokens.add_blacklistedtoken"
                    ),
                },
            )
        await self.send(html)
