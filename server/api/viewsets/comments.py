from django.contrib.contenttypes.models import ContentType
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from comments.models import Comment
from comments.serializers import CommentSerializer
from comments.services import comment_permission_for, create_comment

from api.permissions import check_perm
from .base import OAuth2OnlyMixin


class CommentViewSet(
    OAuth2OnlyMixin, mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """List/create only - the dashboard has no edit or delete UI for comments.

    Commenting on an object is only as visible as the object itself: listing
    requires `content_type`+`object_id` and the matching `view_<model>` perm,
    the same way the dashboard only shows comments on a page you can already view.
    """

    queryset = Comment.objects.select_related("author", "content_type").all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        content_type_id = self.request.query_params.get("content_type")
        object_id = self.request.query_params.get("object_id")
        if not content_type_id or not object_id:
            raise ValidationError("content_type and object_id query params are required.")
        content_type = ContentType.objects.get(pk=content_type_id)
        check_perm(
            self.request,
            f"{content_type.app_label}.view_{content_type.model}",
        )
        return super().get_queryset().filter(content_type=content_type, object_id=object_id)

    def perform_create(self, serializer):
        content_object = serializer.validated_data["content_type"].get_object_for_this_type(
            pk=serializer.validated_data["object_id"]
        )
        check_perm(self.request, comment_permission_for(content_object))
        serializer.instance = create_comment(
            content_object, self.request.user, serializer.validated_data["text"]
        )
