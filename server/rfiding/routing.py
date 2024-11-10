from django.urls import re_path

from space.consumers import SpaceStateConsumer
from tokens.consumers import UnknownTokenConsumer

websocket_urlpatterns = [
    re_path(r"ws/space/status/$", SpaceStateConsumer.as_asgi()),
    re_path(r"ws/tokens/unknown/$", UnknownTokenConsumer.as_asgi()),
]