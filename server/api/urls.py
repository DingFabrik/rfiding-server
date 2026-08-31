from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from api.viewsets.machines import (
    MachineViewSet,
    MachineTimeViewSet,
    MachineRegistrationRequestViewSet,
    MachineControlKeyViewSet,
)
from api.viewsets.people import PersonViewSet, QualificationViewSet
from api.viewsets.tokens import (
    TokenViewSet,
    TokenTypeViewSet,
    UnknownTokenViewSet,
    BlacklistedTokenViewSet,
)
from api.viewsets.access_log import AccessLogViewSet
from api.viewsets.holidays import HolidayViewSet
from api.viewsets.locations import LocationViewSet
from api.viewsets.space import SpaceStateViewSet
from api.viewsets.users import UserViewSet, GroupViewSet, UserWidgetViewSet
from api.viewsets.comments import CommentViewSet
from api.viewsets.firmware import FirmwareViewSet
from api.viewsets.auditlog import AuditLogViewSet

app_name = "api"

router = DefaultRouter()
router.register("machines", MachineViewSet)
router.register("machine-times", MachineTimeViewSet)
router.register("machine-registration-requests", MachineRegistrationRequestViewSet)
router.register("machine-control-keys", MachineControlKeyViewSet)
router.register("people", PersonViewSet)
router.register("qualifications", QualificationViewSet)
router.register("tokens", TokenViewSet)
router.register("token-types", TokenTypeViewSet)
router.register("unknown-tokens", UnknownTokenViewSet)
router.register("blacklisted-tokens", BlacklistedTokenViewSet)
router.register("access-logs", AccessLogViewSet)
router.register("holidays", HolidayViewSet)
router.register("locations", LocationViewSet)
router.register("space-states", SpaceStateViewSet)
router.register("users", UserViewSet)
router.register("groups", GroupViewSet)
router.register("widgets", UserWidgetViewSet, basename="widget")
router.register("comments", CommentViewSet, basename="comment")
router.register("firmware", FirmwareViewSet)
router.register("audit-log", AuditLogViewSet, basename="auditlogentry")

v1_urls = router.urls + [
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="rest:v1:schema"),
        name="swagger-ui",
    ),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="rest:v1:schema"),
        name="redoc",
    ),
]

urlpatterns = [
    path("v1/", include((v1_urls, "api"), namespace="v1")),
]
