from auditlog.models import LogEntry
from rest_framework import serializers


class AuditLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = [
            "id",
            "timestamp",
            "action",
            "content_type",
            "object_pk",
            "object_repr",
            "changes",
            "actor",
            "remote_addr",
        ]
        read_only_fields = fields
