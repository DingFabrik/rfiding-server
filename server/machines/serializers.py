from rest_framework import serializers
from datetime import timedelta

from .models import Machine, MachineTime, MachineRegistrationRequest, MachineControlKey
from .client_modules import (
    ACCESS_CONTROL_MODULES,
    STATUS_DISPLAY_MODULES,
    ACTOR_MODULES,
)


class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = "__all__"
        extra_kwargs = {
            "encryption_key": {"write_only": True},
            "api_key": {"write_only": True},
        }


class MachineTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineTime
        fields = ["id", "machine", "weekdays", "start_time", "end_time"]


class MachineRegistrationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineRegistrationRequest
        fields = ["id", "mac_address", "hostname", "ip_address", "created"]
        read_only_fields = fields


class MachineControlKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineControlKey
        fields = ["key", "machine", "purpose", "last_used", "created"]
        read_only_fields = ["key", "last_used", "created"]


class DurationMillisecondsField(serializers.Field):
    def to_representation(self, value):
        return value.seconds * 1000

    def to_internal_value(self, data):
        return timedelta(milliseconds=data)


class MachineConfigSerializer(serializers.Serializer):
    runtimer = DurationMillisecondsField(default=0)
    minPower = serializers.IntegerField(default=0, min_value=0)
    controlParameter = serializers.IntegerField(default=None)
    display_time_countdown = serializers.BooleanField(default=True)
    display_power_consumption = serializers.BooleanField(default=True)
    link_relays = serializers.BooleanField(default=False)

    accessControlModule = serializers.ChoiceField(
        choices=ACCESS_CONTROL_MODULES, default=0
    )
    accessControlModuleSettings = serializers.JSONField(default=dict, required=False)
    statusDisplayModule = serializers.ChoiceField(
        choices=STATUS_DISPLAY_MODULES, default=0
    )
    statusDisplayModuleSettings = serializers.JSONField(default=dict, required=False)
    actorModule = serializers.ChoiceField(choices=ACTOR_MODULES, default=0)
    actorModuleSettings = serializers.JSONField(default=dict, required=False)
