from django.urls import path

from . import views

app_name = "holidays"

urlpatterns = [
    path("", views.HolidayListView.as_view(), name="list"),
    path("add", views.HolidayCreateView.as_view(), name="create"),
    path("<int:pk>", views.HolidayUpdateView.as_view(), name="update"),
    path("<int:pk>/delete", views.HolidayDeleteView.as_view(), name="delete"),
]
