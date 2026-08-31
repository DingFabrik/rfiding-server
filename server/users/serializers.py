from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import RFIDingUser, UserWidget


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = RFIDingUser
        exclude = ["user_permissions"]
        read_only_fields = ["last_login", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = RFIDingUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class UserWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserWidget
        fields = ["id", "user", "widget", "position", "width", "settings"]
        read_only_fields = ["user"]
