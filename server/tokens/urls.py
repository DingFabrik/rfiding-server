from django.urls import path

from . import views

app_name = "tokens"

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
]
