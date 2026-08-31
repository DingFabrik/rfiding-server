from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from space.models import SpaceState
from space.common import get_current_space_state
from space.serializers import SpaceStateSerializer
from .base import OAuth2OnlyMixin


class SpaceStateViewSet(OAuth2OnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SpaceState.objects.all()
    serializer_class = SpaceStateSerializer

    @action(detail=False, methods=["get"])
    def current(self, request):
        return Response(self.get_serializer(get_current_space_state()).data)
