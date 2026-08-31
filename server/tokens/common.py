from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import UnknownToken, BlacklistedToken

channel_layer = get_channel_layer()


def clear_unknown_tokens():
    UnknownToken.objects.all().delete()
    async_to_sync(channel_layer.group_send)(
        "unknown_tokens", {"type": "unknown_token_list_changed"}
    )


def blacklist_token(serial):
    UnknownToken.objects.filter(serial=serial).delete()
    return BlacklistedToken.objects.create(serial=serial)
