from django.contrib.auth.models import Group
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from users.models import RFIDingUser, UserWidget
from users.serializers import UserSerializer, GroupSerializer, UserWidgetSerializer

from api.permissions import check_perm
from .base import BaseModelViewSet


class UserViewSet(BaseModelViewSet):
    queryset = RFIDingUser.objects.all()
    serializer_class = UserSerializer
    search_fields = ["name", "email"]
    ordering_fields = ["email", "name"]

    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        user = self.get_object()
        if request.user.pk != user.pk:
            check_perm(request, "users.change_rfidinguser")
        password = request.data.get("password")
        if not password:
            raise ValidationError({"password": "This field is required."})
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


class UserWidgetViewSet(BaseModelViewSet):
    """Widgets on the current user's own dashboard home page."""

    queryset = UserWidget.objects.all()
    serializer_class = UserWidgetSerializer

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
