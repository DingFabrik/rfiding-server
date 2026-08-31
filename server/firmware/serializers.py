from rest_framework import serializers

from .models import Firmware


class FirmwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Firmware
        fields = ["id", "name", "version", "file", "created", "updated"]
