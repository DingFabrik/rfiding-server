from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentType.objects.all())
    author_name = serializers.CharField(source="author.name", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "text",
            "author",
            "author_name",
            "content_type",
            "object_id",
            "created",
            "updated",
        ]
        read_only_fields = ["author", "created", "updated"]
