from django.urls import path, include

from . import views

app_name = "users"

groups_patterns = [
    path("", views.GroupListView.as_view(), name="list"),
    path("add", views.GroupCreateView.as_view(), name="create"),
    path("<int:pk>", views.GroupUpdateView.as_view(), name="update"),
    path("<int:pk>/delete", views.GroupDeleteView.as_view(), name="delete"),
]

urlpatterns = [
    path("profile", views.ProfileView.as_view(), name="profile"),
    path("", views.UserListView.as_view(), name="list"),
    path("add", views.UserCreateView.as_view(), name="create"),
    path("<int:pk>", views.UserDetailView.as_view(), name="detail"),
    path("<int:pk>/modify", views.UserUpdateView.as_view(), name="update"),
    path("<int:pk>/delete", views.UserDeleteView.as_view(), name="delete"),
    path("<int:pk>/change-password", views.AdminChangePasswordView.as_view(), name="admin_change_password"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change_password"
    ),
    path("groups/", include((groups_patterns, "groups"), namespace="groups")),
]
