from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from tokens.models import Token, TokenType, UnknownToken, BlacklistedToken
from tokens.filters import TokenFilterSet
from tokens.common import clear_unknown_tokens, blacklist_token
from tokens.serializers import (
    TokenSerializer,
    TokenTypeSerializer,
    UnknownTokenSerializer,
    BlacklistedTokenSerializer,
)

from api.permissions import check_perm
from .base import BaseModelViewSet, OAuth2OnlyMixin


class TokenViewSet(BaseModelViewSet):
    queryset = Token.objects.select_related("person", "type").all()
    serializer_class = TokenSerializer
    filterset_class = TokenFilterSet
    search_fields = ["serial", "purpose"]
    ordering_fields = ["serial", "purpose", "updated", "created"]

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        self.check_perm("tokens.change_token")
        token = self.get_object().toggle_active()
        return Response(self.get_serializer(token).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        self.check_perm("tokens.delete_token")
        token = self.get_object().archive()
        return Response(self.get_serializer(token).data)

    @action(detail=False, methods=["post"])
    def assign(self, request):
        self.check_perm("tokens.add_token")
        if not request.data.get("serial"):
            raise ValidationError({"serial": "This field is required."})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.save()
        UnknownToken.objects.filter(serial=token.serial).delete()
        return Response(self.get_serializer(token).data, status=201)

    @action(detail=False, methods=["get"], url_path="next-label")
    def next_label(self, request):
        token_type_id = request.query_params.get("type")
        tokens = Token.objects.filter(label_id__isnull=False)
        if token_type_id:
            token_type = TokenType.objects.get(pk=token_type_id)
            tokens = tokens.filter(type=token_type)
            label_format = token_type.format_label_id
        else:
            tokens = tokens.filter(type__isnull=True)
            label_format = lambda x: f"{x}"  # noqa: E731
        last = tokens.order_by("-label_id").first()
        next_id = (last.label_id + 1) if last and last.label_id else 1
        return Response({"label_id": next_id, "label": label_format(next_id)})


class TokenTypeViewSet(BaseModelViewSet):
    queryset = TokenType.objects.all()
    serializer_class = TokenTypeSerializer


class UnknownTokenViewSet(OAuth2OnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = UnknownToken.objects.select_related("machine").all()
    serializer_class = UnknownTokenSerializer

    @action(detail=False, methods=["post"])
    def clear(self, request):
        check_perm(request, "tokens.delete_unknowntoken")
        clear_unknown_tokens()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def blacklist(self, request, pk=None):
        check_perm(request, "tokens.add_blacklistedtoken")
        unknown_token = self.get_object()
        blacklisted = blacklist_token(unknown_token.serial)
        return Response(BlacklistedTokenSerializer(blacklisted).data, status=201)


class BlacklistedTokenViewSet(BaseModelViewSet):
    queryset = BlacklistedToken.objects.all()
    serializer_class = BlacklistedTokenSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
