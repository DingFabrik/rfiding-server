from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .common import get_current_space_state, update_space_state
from .secret import SECRET_HEADER, is_valid_space_secret


class APISpaceStatusView(APIView):
    """Read the space state, or change it with the shared SPACE_STATE_SECRET.

    To change the state, POST `state` with the secret in the `X-Space-Secret`
    header (or a `secret` body field). Passing `secret`/`state` as GET query
    parameters still works for existing clients but is deprecated, because the
    secret then ends up in proxy and access logs.
    """

    permission_classes = [permissions.AllowAny]
    # Clients authenticate with the shared secret only; session auth would
    # demand a CSRF token from logged-in browsers for no benefit.
    authentication_classes = []

    def get(self, request, format=None):
        secret = request.headers.get(SECRET_HEADER, request.GET.get("secret", None))
        if secret is not None:
            return self.change_state(secret, request.GET.get("state", None))
        current_state = get_current_space_state()
        return Response(
            {"open": current_state.is_open, "changed_at": current_state.updated},
            status=status.HTTP_200_OK,
        )

    def post(self, request, format=None):
        secret = request.headers.get(SECRET_HEADER, request.data.get("secret", None))
        return self.change_state(secret, request.data.get("state", None))

    def change_state(self, secret, new_state):
        if not is_valid_space_secret(secret):
            return Response(
                {"error": "invalid secret"}, status=status.HTTP_403_FORBIDDEN
            )
        if new_state is None:
            return Response(
                {"error": "missing state"}, status=status.HTTP_400_BAD_REQUEST
            )
        state = update_space_state(new_state)
        return Response({"open": state.is_open}, status=status.HTTP_200_OK)
