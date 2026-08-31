from firmware.models import Firmware
from firmware.serializers import FirmwareSerializer

from .base import BaseModelViewSet


class FirmwareViewSet(BaseModelViewSet):
    queryset = Firmware.objects.all()
    serializer_class = FirmwareSerializer
    search_fields = ["name", "version"]
