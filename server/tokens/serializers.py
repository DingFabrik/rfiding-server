from rest_framework import serializers

from .models import Token, TokenType, UnknownToken, BlacklistedToken


class TokenTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenType
        fields = "__all__"


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = "__all__"
        read_only_fields = ["archived"]


class UnknownTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnknownToken
        fields = ["id", "serial", "machine", "created", "updated"]
        read_only_fields = fields


class BlacklistedTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistedToken
        fields = "__all__"
