"""Which requests Silk records (SILKY_INTERCEPT_FUNC)."""

import random

from django.conf import settings

# Silk never masks response bodies, so these would store OAuth access tokens and
# client secrets.
NOT_RECORDED_PATH_PREFIXES = ("/api/rest/v1/oauth/",)


def should_record(request):
    """Records SILKY_INTERCEPT_PERCENT of requests, except for NOT_RECORDED_PATH_PREFIXES.

    Silk ignores SILKY_INTERCEPT_PERCENT once SILKY_INTERCEPT_FUNC is set, so the
    sampling is done here.
    """
    if request.path_info.startswith(NOT_RECORDED_PATH_PREFIXES):
        return False
    return random.random() * 100 < settings.SILKY_INTERCEPT_PERCENT
