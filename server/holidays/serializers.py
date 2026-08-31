from rest_framework import serializers

from .models import Holiday


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "name", "date", "repeats_annually"]
