from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("profile", views.ProfileView.as_view(), name="profile"),
    path("users", views.UserListView.as_view(), name="list"),
    path("users/add", views.UserCreateView.as_view(), name="create"),
    path("users/<int:pk>/modify", views.UserUpdateView.as_view(), name="update"),
    path("users/<int:pk>/delete", views.UserDeleteView.as_view(), name="delete"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change_password"
    ),
]
