from locations.models import Location
from locations.serializers import LocationSerializer

from .base import BaseModelViewSet


class LocationViewSet(BaseModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "updated", "created"]
