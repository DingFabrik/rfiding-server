from django.urls import re_path

from space.consumers import SpaceStateConsumer

websocket_urlpatterns = [
    re_path(r"ws/space/status/$", SpaceStateConsumer.as_asgi()),
]