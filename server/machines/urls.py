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
        "<int:pk>/status",
        views.MachineStatusPartialView.as_view(),
        name="status",
    ),
    path("<int:pk>/delete", views.MachineDeleteView.as_view(), name="delete"),
    path("<int:pk>/logs", views.MachineLogView.as_view(), name="logs"),
    path("autocomplete", ajax.MachineAutocompleteView.as_view(), name="autocomplete"),
    path(
        "autocomplete/qualify/<int:person>",
        ajax.QualifyableMachineAutocompleteView.as_view(),
        name="autocomplete-qualifyable",
    ),
    path(
        "<int:pk>/qualifications",
        views.MachineQualificationsListView.as_view(),
        name="qualifications",
    ),
    path(
        "<int:pk>/qualifications/qualify",
        views.QualifyMachineView.as_view(),
        name="qualify",
    ),
    path(
        "<int:pk>/instructors",
        views.MachineInstructorListView.as_view(),
        name="instructors",
    ),
    path(
        "<int:pk>/statistics",
        views.MachineStatisticsView.as_view(),
        name="statistics",
    ),
    path(
        "requests/<int:pk>/delete",
        views.MachineRegistrationRequestDeleteView.as_view(),
        name="delete-request",
    ),
    path(
        "popover",
        views.MachinePopoverView.as_view(),
        name="popover",
    ),
    path(
        "<int:pk>/comments/add",
        views.MachineCommentCreateView.as_view(),
        name="add-comment",
    ),
]
