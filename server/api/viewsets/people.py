from rest_framework.decorators import action
from rest_framework.response import Response

from base.services import toggle_active
from people.models import Person, Qualification
from people.filters import PersonFilterSet
from people.serializers import PersonSerializer, QualificationSerializer
from comments.serializers import CommentSerializer
from comments.services import comment_permission_for, create_comment
from comments.models import Comment
from django.contrib.contenttypes.models import ContentType

from api.permissions import ActionPermission, check_perm
from .base import BaseModelViewSet


class QualificationPermission(ActionPermission):
    read_perm = "people.view_qualification"
    write_perm = "people.qualify_person"


class PersonViewSet(BaseModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    filterset_class = PersonFilterSet
    search_fields = ["name", "email", "member_id"]
    ordering_fields = ["member_id", "name", "email", "updated", "created"]

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        self.check_perm("people.change_person")
        person = toggle_active(self.get_object())
        return Response(self.get_serializer(person).data)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        person = self.get_object()
        perm = comment_permission_for(person)
        check_perm(request, perm)
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = create_comment(person, request.user, serializer.validated_data["text"])
            return Response(CommentSerializer(comment).data, status=201)
        content_type = ContentType.objects.get_for_model(Person)
        comments = Comment.objects.filter(content_type=content_type, object_id=person.pk)
        return Response(CommentSerializer(comments, many=True).data)


class QualificationViewSet(BaseModelViewSet):
    queryset = Qualification.objects.select_related("person", "machine", "instructed_by").all()
    serializer_class = QualificationSerializer
    permission_classes = [QualificationPermission]
    ordering_fields = ["created", "updated", "expires_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        person = self.request.query_params.get("person")
        machine = self.request.query_params.get("machine")
        if person is not None:
            queryset = queryset.filter(person=person)
        if machine is not None:
            queryset = queryset.filter(machine=machine)
        return queryset
