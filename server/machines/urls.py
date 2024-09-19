from django.urls import path

from . import views
from . import ajax

app_name = "machines"

urlpatterns = [
    path("", views.MachineListView.as_view(), name="list"),
    path("<int:pk>", views.MachineDetailView.as_view(), name="detail"),
    path("add", views.MachineCreateView.as_view(), name="create"),
    path("<int:pk>/modify", views.MachineUpdateView.as_view(), name="update"),
    path("<int:pk>/configure", views.MachineConfigureView.as_view(), name="configure"),
    path(
        "<int:pk>/toggle_active",
        views.MachineToggleActiveView.as_view(),
        name="toggle-active",
    ),
    path("<int:pk>/delete", views.MachineDeleteView.as_view(), name="delete"),
    path("autocomplete", ajax.MachineAutocompleteView.as_view(), name="autocomplete"),
    path(
        "autocomplete/qualify/<int:person>",
        ajax.QualifyableMachineAutocompleteView.as_view(),
        name="autocomplete-qualifyable",
    ),
    path(
        "autocomplete/instructor/<int:person>",
        ajax.InstructorMachineAutocompleteView.as_view(),
        name="autocomplete-instructor",
    ),
]
