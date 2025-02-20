from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("", views.LocationListView.as_view(), name="list"),
    path("<int:pk>", views.LocationDetailView.as_view(), name="detail"),
    path("add", views.LocationCreateView.as_view(), name="create"),
    path("<int:pk>/modify", views.LocationUpdateView.as_view(), name="update"),
    path("<int:pk>/delete", views.LocationDeleteView.as_view(), name="delete"),
]
