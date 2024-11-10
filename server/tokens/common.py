from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import UnknownToken

channel_layer = get_channel_layer()

def clear_unknown_tokens():
    UnknownToken.objects.all().delete()
    async_to_sync(channel_layer.group_send)("unknown_tokens", {"type": "unknown_token_list_changed"})