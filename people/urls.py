from django.urls import path

from people.views import PersonCreateView, PersonDetailView, PersonListView, PersonUpdateView

app_name = "people"
urlpatterns = [
    path("", PersonListView.as_view(), name="list"),
    path("<int:pk>/", PersonDetailView.as_view(), name="detail"),
    path("add/", PersonCreateView.as_view(), name="create"),
    path("<int:pk>/update", PersonUpdateView.as_view(), name="update"),
]