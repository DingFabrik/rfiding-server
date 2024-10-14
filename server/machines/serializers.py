from rest_framework import serializers

from .models import Machine
from .client_modules import ACCESS_CONTROL_MODULES, STATUS_DISPLAY_MODULES, ACTOR_MODULES


class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = "__all__"


class MachineConfigSerializer(serializers.Serializer):
    runtimer = serializers.IntegerField(default=0, min_value=0)
    minPower = serializers.IntegerField(default=0, min_value=0)
    controlParameter = serializers.IntegerField(default=None)

    accessControlModule = serializers.ChoiceField(choices=ACCESS_CONTROL_MODULES, default=0)
    accessControlModuleSettings = serializers.JSONField(default=dict, required=False)
    statusDisplayModule = serializers.ChoiceField(choices=STATUS_DISPLAY_MODULES, default=0)
    statusDisplayModuleSettings = serializers.JSONField(default=dict, required=False)
    actorModule = serializers.ChoiceField(choices=ACTOR_MODULES, default=0)
    actorModuleSettings = serializers.JSONField(default=dict, required=False)
