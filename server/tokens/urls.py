from django.urls import path, include

from . import views

app_name = "tokens"

token_type_patterns = [
    path("", views.TokenTypeListView.as_view(), name="list"),
    path("add", views.TokenTypeCreateView.as_view(), name="create"),
    path("<int:pk>/modify", views.TokenTypeUpdateView.as_view(), name="update"),
    path("<int:pk>/delete", views.TokenTypeDeleteView.as_view(), name="delete"),
]

urlpatterns = [
    path("", views.TokenListView.as_view(), name="list"),
    path("<int:pk>", views.TokenDetailView.as_view(), name="detail"),
    path("add", views.TokenCreateView.as_view(), name="create"),
    path("<int:pk>/modify", views.TokenUpdateView.as_view(), name="update"),
    path(
        "<int:pk>/toggle_active",
        views.TokenToggleActiveView.as_view(),
        name="toggle-active",
    ),
    path("<int:pk>/archive", views.TokenArchiveView.as_view(), name="delete"),
    path("assign/<str:serial>", views.AssignTokenView.as_view(), name="assign"),
    path("unknown", views.UnknownTokenListView.as_view(), name="unknown"),
    path("unknown/clear", views.ClearUnknownTokensView.as_view(), name="clear-unknown"),
    path("blacklisted", views.BlacklistedTokenListView.as_view(), name="blacklisted"),
    path(
        "unknown/<str:serial>/blacklist",
        views.BlacklistTokenView.as_view(),
        name="blacklist-token",
    ),
    path(
        "blacklisted/<int:pk>/delete",
        views.BlacklistedTokenDeleteView.as_view(),
        name="delete-blacklisted",
    ),
    path(
        "person-for-token",
        views.PersonForTokenPopoverView.as_view(),
        name="person-for-token-popover",
    ),
    path("next-label", views.NextFreeTokenLabelView.as_view(), name="next-label-id"),
    path("types/", include((token_type_patterns, "types"), namespace="types")),
]
