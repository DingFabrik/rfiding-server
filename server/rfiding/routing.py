from django.urls import re_path

from space.consumers import SpaceStateConsumer
from tokens.consumers import UnknownTokenConsumer
from machines.consumers import MachineStateConsumer, MachineLogConsumer

websocket_urlpatterns = [
    re_path(r"ws/space/status/$", SpaceStateConsumer.as_asgi()),
    re_path(r"ws/tokens/unknown/$", UnknownTokenConsumer.as_asgi()),
    re_path(r"ws/machines/(?P<mac_address>([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))/state", MachineStateConsumer.as_asgi()),
    re_path(r"ws/machines/(?P<mac_address>([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))/logs", MachineLogConsumer.as_asgi())
]