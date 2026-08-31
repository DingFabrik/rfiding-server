from rest_framework import viewsets

from access_log.models import AccessLog
from access_log.filters import AccessLogFilterSet
from access_log.serializers import AccessLogSerializer

from .base import OAuth2OnlyMixin


class AccessLogViewSet(OAuth2OnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AccessLog.objects.select_related("token", "machine").order_by("-timestamp")
    serializer_class = AccessLogSerializer
    filterset_class = AccessLogFilterSet
    ordering_fields = ["timestamp"]

    def get_queryset(self):
        queryset = super().get_queryset()
        token = self.request.query_params.get("token")
        person = self.request.query_params.get("person")
        machine = self.request.query_params.get("machine")
        if token is not None:
            queryset = queryset.filter(token__pk=token)
        if person is not None:
            queryset = queryset.filter(token__person__pk=person)
        if machine is not None:
            queryset = queryset.filter(machine__pk=machine)
        return queryset
