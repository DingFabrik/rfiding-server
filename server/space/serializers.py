from rest_framework import serializers

from .models import SpaceState


class SpaceStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceState
        fields = ["id", "is_open", "created", "updated"]
        read_only_fields = fields
