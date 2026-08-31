from rest_framework import serializers

from .models import Person, Qualification


class PersonSerializer(serializers.ModelSerializer):
    detail_key_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Person
        fields = "__all__"
        read_only_fields = ["detail_key", "detail_key_expires_at"]


class QualificationSerializer(serializers.ModelSerializer):
    expires_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Qualification
        fields = "__all__"
        read_only_fields = ["last_used", "expires_at", "expired"]
