from rest_framework import serializers

from machines.models import Machine

class MachineConfigSerializer(serializers.ModelSerializer):
    minPower = serializers.IntegerField(source='min_power')
    controlParameter = serializers.CharField(source='control_parameter')
    class Meta:
        model = Machine
        fields = ['runtimer', 'minPower', 'controlParameter']

class AccessGrantedSerializer(serializers.Serializer):
    access = serializers.BooleanField()
    workingTime = serializers.IntegerField()