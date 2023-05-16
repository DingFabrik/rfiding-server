from django.urls import path

from tokens.views import TokenListView

app_name = "tokens"
urlpatterns = [
    path("", TokenListView.as_view(), name="list"),
]