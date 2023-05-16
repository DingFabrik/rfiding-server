from django.urls import path

from machines.views import MachineDetailView, MachineListView

app_name = "machines"
urlpatterns = [
    path("", MachineListView.as_view(), name="list"),
    path("<int:pk>/", MachineDetailView.as_view(), name="detail"),
]