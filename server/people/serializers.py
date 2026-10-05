from rest_framework import serializers

from .models import Person, Qualification


class PersonSerializer(serializers.ModelSerializer):
    detail_key_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Person
        fields = "__all__"
        # slack_conversation_id is managed by the Slack integration, not by users.
        read_only_fields = ["detail_key", "detail_key_expires_at", "slack_conversation_id"]

    # System maintainers can unlock every machine in maintenance mode, so like in
    # the dashboard (where only Django admin exposes it) only superusers may set it.
    SUPERUSER_ONLY_FIELDS = ["is_system_maintainer"]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is None or not request.user.is_superuser:
            for name in self.SUPERUSER_ONLY_FIELDS:
                fields[name].read_only = True
        return fields


class QualificationSerializer(serializers.ModelSerializer):
    expires_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Qualification
        fields = "__all__"
        read_only_fields = ["last_used", "expires_at", "expired"]

    # Appointing instructors and maintainers needs more than `qualify_person`.
    INSTRUCTOR_FIELDS = ["is_instructor", "is_maintainer"]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is None or not request.user.has_perm("people.change_instructor"):
            for name in self.INSTRUCTOR_FIELDS:
                fields[name].read_only = True
        return fields
