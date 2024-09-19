from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings as SETTINGS

from .models import SpaceState


class APISpaceStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        current_state = SpaceState.objects.first()
        is_open = False
        if current_state is not None:
            is_open = current_state.is_open
        if request.GET.get("secret", None) is not None:
            if request.GET.get("secret", None) != SETTINGS.SPACE_STATE_SECRET:
                return Response(
                    {"error": "invalid secret"}, status=status.HTTP_403_FORBIDDEN
                )
            new_state = request.GET.get("state", None)
            if new_state is None:
                return Response(
                    {"error": "missing state"}, status=status.HTTP_400_BAD_REQUEST
                )
            if new_state == "1":
                new_state = True
            elif new_state == "0":
                new_state = False
            if new_state == is_open:
                return Response(
                    {"open": is_open, "changed_at": current_state.updated},
                    status=status.HTTP_200_OK,
                )
            state = SpaceState.objects.create(is_open=new_state)
            state.save()
            return Response({"open": state.is_open}, status=status.HTTP_200_OK)
        return Response(
            {"open": current_state.is_open, "changed_at": current_state.updated},
            status=status.HTTP_200_OK,
        )
