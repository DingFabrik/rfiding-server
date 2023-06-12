from django.urls import path

from machines.views import MachineCreateView, MachineDetailView, MachineListView, MachineUpdateView

app_name = "machines"
urlpatterns = [
    path("", MachineListView.as_view(), name="list"),
    path("<int:pk>/", MachineDetailView.as_view(), name="detail"),
    path("add/", MachineCreateView.as_view(), name="create"),
    path("<int:pk>/update", MachineUpdateView.as_view(), name="update"),
]