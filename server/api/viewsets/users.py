from django.contrib.auth import password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from users.models import RFIDingUser, UserWidget
from users.permissions import (
    check_can_modify_group,
    check_can_modify_user,
    check_within_own_permissions,
    permission_names,
)
from users.serializers import UserSerializer, GroupSerializer, UserWidgetSerializer

from api.permissions import check_perm
from .base import BaseModelViewSet


class UserViewSet(BaseModelViewSet):
    queryset = RFIDingUser.objects.all()
    serializer_class = UserSerializer
    search_fields = ["name", "email"]
    ordering_fields = ["email", "name"]

    def get_permissions(self):
        # Acting on your own account needs no model permission; change_password
        # checks `change_rfidinguser` itself when targeting another user.
        if self.action in ("me", "change_password"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_update(self, serializer):
        check_can_modify_user(self.request.user, serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        check_can_modify_user(self.request.user, instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        user = self.get_object()
        if request.user.pk != user.pk:
            check_perm(request, "users.change_rfidinguser")
            check_can_modify_user(request.user, user)
        elif not user.check_password(request.data.get("old_password") or ""):
            # Like the dashboard's PasswordChangeForm: a leaked OAuth token
            # alone must not be enough to take over the account.
            raise ValidationError({"old_password": "Incorrect password."})
        password = request.data.get("password")
        if not password:
            raise ValidationError({"password": "This field is required."})
        try:
            password_validation.validate_password(password, user)
        except DjangoValidationError as e:
            raise ValidationError({"password": list(e.messages)}) from None
        user.set_password(password)
        user.save()
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(self.get_serializer(request.user).data)


class GroupViewSet(BaseModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    search_fields = ["name"]

    def check_new_permissions(self, serializer):
        check_within_own_permissions(
            self.request.user,
            permission_names(serializer.validated_data.get("permissions", [])),
        )

    def perform_create(self, serializer):
        self.check_new_permissions(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        check_can_modify_group(self.request.user, serializer.instance)
        self.check_new_permissions(serializer)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        check_can_modify_group(self.request.user, instance)
        super().perform_destroy(instance)


class UserWidgetViewSet(BaseModelViewSet):
    """Widgets on the current user's own dashboard home page."""

    queryset = UserWidget.objects.all()
    serializer_class = UserWidgetSerializer
    # get_queryset scopes everything to request.user's own widgets.
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.widgets.all()

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user, position=self.request.user.widgets.count()
        )

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        order = request.data.get("order", [])
        widgets_by_pk = {str(widget.pk): widget for widget in self.get_queryset()}
        updated = []
        for position, pk in enumerate(order):
            widget = widgets_by_pk.get(str(pk))
            if widget is not None:
                widget.position = position
                updated.append(widget)
        UserWidget.objects.bulk_update(updated, ["position"])
        return Response(status=204)
