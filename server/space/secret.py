import hmac

from django.conf import settings

SECRET_HEADER = "X-Space-Secret"


def is_valid_space_secret(provided):
    """Check a client-supplied secret against SPACE_STATE_SECRET.

    An empty or unset SPACE_STATE_SECRET never matches: otherwise an empty
    `secret` from the client would compare equal and anyone could change the
    space state.
    """
    expected = getattr(settings, "SPACE_STATE_SECRET", "") or ""
    if not expected or not isinstance(provided, str) or not provided:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())
