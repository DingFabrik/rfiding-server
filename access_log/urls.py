from django.urls import path

from . import views

app_name = "access_log"

urlpatterns = [
    path("", views.AccessLogListView.as_view(), name="list"),
    path(
        "token/<int:token>",
        views.AccessLogForTokenView.as_view(),
        name="for-token",
    ),
path(
        "person/<int:person>",
        views.AccessLogForPersonView.as_view(),
        name="for-person",
    ),
    path(
        "machine/<int:machine>",
        views.AccessLogForMachineView.as_view(),
        name="for-machine",
    ),
]
