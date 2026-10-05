from django.contrib.auth import password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import RFIDingUser, UserWidget


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = RFIDingUser
        exclude = ["user_permissions"]
        read_only_fields = ["last_login", "date_joined"]

    # Granting these escalates privileges, so `change_rfidinguser` alone isn't enough.
    SUPERUSER_ONLY_FIELDS = ["is_superuser", "is_staff", "groups"]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is None or not request.user.is_superuser:
            for name in self.SUPERUSER_ONLY_FIELDS:
                fields[name].read_only = True
        return fields

    def validate_password(self, value):
        request = self.context.get("request")
        if (
            self.instance is not None
            and request is not None
            and self.instance.pk == request.user.pk
        ):
            # Like the dashboard: changing your own password needs the old one,
            # which only the change-password action asks for.
            raise serializers.ValidationError(
                "Use the change-password action to change your own password."
            )
        try:
            password_validation.validate_password(value, self.instance)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from None
        return value

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
