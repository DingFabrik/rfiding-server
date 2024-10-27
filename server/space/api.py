from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings as SETTINGS

from .models import SpaceState
from .common import get_current_space_state, update_space_state

class APISpaceStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
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
            state = update_space_state(new_state)
            return Response({"open": state.is_open}, status=status.HTTP_200_OK)
        current_state = get_current_space_state()
        return Response(
            {"open": current_state.is_open, "changed_at": current_state.updated},
            status=status.HTTP_200_OK,
        )
