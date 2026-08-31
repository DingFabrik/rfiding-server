from auditlog.models import LogEntry
from rest_framework import viewsets
from rest_framework.permissions import BasePermission

from base.serializers import AuditLogEntrySerializer
from .base import OAuth2OnlyMixin


class HasAuditLogPermission(BasePermission):
    def has_permission(self, request, view):
        # mirrors base.views.AuditlogView.permission_required
        return request.user.has_perm("tokens.view_token")


class AuditLogViewSet(OAuth2OnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LogEntry.objects.select_related("content_type").order_by("-timestamp")
    serializer_class = AuditLogEntrySerializer
    search_fields = ["object_repr"]
    ordering_fields = ["timestamp"]
    permission_classes = [HasAuditLogPermission]
