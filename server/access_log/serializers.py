from rest_framework import serializers

from .models import AccessLog


class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = [
            "id",
            "timestamp",
            "token",
            "machine",
            "enabled_duration",
            "type",
            "unsuccessful_reason",
        ]
        read_only_fields = fields
