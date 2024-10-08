from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("profile", views.ProfileView.as_view(), name="profile"),
    path("users", views.UserListView.as_view(), name="list"),
    path("users/add", views.UserCreateView.as_view(), name="create"),
    path("users/<int:pk>", views.UserDetailView.as_view(), name="detail"),
    path("users/<int:pk>/modify", views.UserUpdateView.as_view(), name="update"),
    path("users/<int:pk>/delete", views.UserDeleteView.as_view(), name="delete"),
    path("users/<int:pk>/change-password", views.AdminChangePasswordView.as_view(), name="admin_change_password"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change_password"
    ),
]
