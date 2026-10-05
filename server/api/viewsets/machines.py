from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType

from machines.models import Machine, MachineTime, MachineRegistrationRequest, MachineControlKey
from machines.filters import MachineFilterSet
from machines.statistics import compute_machine_statistics
from machines.serializers import (
    MachineSerializer,
    MachineTimeSerializer,
    MachineRegistrationRequestSerializer,
    MachineControlKeySerializer,
)
from people.models import Qualification
from people.serializers import QualificationSerializer
from comments.models import Comment
from comments.serializers import CommentSerializer
from comments.services import comment_permission_for, create_comment

from api.permissions import check_perm
from .base import BaseModelViewSet, OAuth2OnlyMixin


class MachineViewSet(BaseModelViewSet):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer
    filterset_class = MachineFilterSet
    search_fields = ["name", "hostname", "mac_address"]
    ordering_fields = ["name", "hostname", "ip_address", "mac_address", "updated"]

    @action(detail=True, methods=["get"])
    def qualifications(self, request, pk=None):
        self.check_perm("people.view_qualification")
        qualifications = Qualification.objects.filter(machine=pk).select_related(
            "person", "instructed_by"
        )
        page = self.paginate_queryset(qualifications)
        serializer = QualificationSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def qualify(self, request, pk=None):
        self.check_perm("people.qualify_person")
        machine = self.get_object()
        serializer = QualificationSerializer(
            data={**request.data, "machine": machine.pk},
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get"])
    def instructors(self, request, pk=None):
        self.check_perm("people.view_qualification")
        instructors = Qualification.objects.filter(
            machine=pk, is_instructor=True
        ).select_related("person")
        page = self.paginate_queryset(instructors)
        serializer = QualificationSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        machine = self.get_object()
        days = int(request.query_params.get("days", 90))
        return Response(compute_machine_statistics(machine, days))

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        machine = self.get_object()
        perm = comment_permission_for(machine)
        check_perm(request, perm)
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = create_comment(machine, request.user, serializer.validated_data["text"])
            return Response(CommentSerializer(comment).data, status=201)
        content_type = ContentType.objects.get_for_model(Machine)
        comments = Comment.objects.filter(content_type=content_type, object_id=machine.pk)
        return Response(CommentSerializer(comments, many=True).data)


class MachineTimeViewSet(BaseModelViewSet):
    queryset = MachineTime.objects.all()
    serializer_class = MachineTimeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        machine = self.request.query_params.get("machine")
        if machine is not None:
            queryset = queryset.filter(machine=machine)
        return queryset


class MachineRegistrationRequestViewSet(
    OAuth2OnlyMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """List/delete only - requests are created by the machine-facing API, never the dashboard."""

    queryset = MachineRegistrationRequest.objects.all()
    serializer_class = MachineRegistrationRequestSerializer


class MachineControlKeyViewSet(BaseModelViewSet):
    queryset = MachineControlKey.objects.all()
    serializer_class = MachineControlKeySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        machine = self.request.query_params.get("machine")
        if machine is not None:
            queryset = queryset.filter(machine=machine)
        return queryset
