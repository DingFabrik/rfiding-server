from django.urls import path

from . import views

app_name = "access_log"

urlpatterns = [
    path("", views.AccessLogListView.as_view(), name="list"),
    path(
        "for_token/<int:token>",
        views.AccessLogForTokenSnippet.as_view(),
        name="for-token",
    ),
]
