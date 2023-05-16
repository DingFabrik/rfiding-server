from rest_framework import serializers

from machines.models import Machine

class MachineConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = ['runtimer', 'min_power', 'control_parameter']