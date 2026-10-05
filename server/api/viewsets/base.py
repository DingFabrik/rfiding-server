from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from rest_framework import viewsets
from rest_framework.throttling import UserRateThrottle

from api.permissions import check_perm


class OAuth2OnlyMixin:
    """Authenticate `/api/rest/` requests via OAuth2 only.

    The project-wide `DEFAULT_AUTHENTICATION_CLASSES` also lists session/basic
    auth for the pre-existing dashboard-internal ajax endpoints (they rely on
    the logged-in browser session); this admin API is OAuth2-only as requested.
    """

    authentication_classes = [OAuth2Authentication]
    throttle_classes = [UserRateThrottle]

    def check_permissions(self, request):
        """Also require the token's scope: `read` for safe methods, `write` otherwise.

        Done here rather than via `permission_classes`, because several viewsets
        replace those (or override `get_permissions()`), and the scope check must
        apply to every endpoint and custom action regardless.
        """
        super().check_permissions(request)
        if not TokenHasReadWriteScope().has_permission(request, self):
            self.permission_denied(
                request,
                message="Token is missing the required scope for this request.",
                code="insufficient_scope",
            )


class BaseModelViewSet(OAuth2OnlyMixin, viewsets.ModelViewSet):
    """Common base for admin-API viewsets.

    Filtering/search/ordering backends are wired globally via
    `REST_FRAMEWORK["DEFAULT_FILTER_BACKENDS"]` (base.filtering.DRFFilterBackend +
    DRF's SearchFilter/OrderingFilter) - subclasses just set `filterset_class`,
    `search_fields`, `ordering_fields` the same way dashboard `BaseListView`
    subclasses set `filterset_class`/`search_field`/`sort_fields`.
    """

    def check_perm(self, perm):
        check_perm(self.request, perm)
