from django.urls import path

from . import views
from . import ajax

app_name = "people"

urlpatterns = [
    path("", views.PersonListView.as_view(), name="list"),
    path("<int:pk>", views.PersonDetailView.as_view(), name="detail"),
    path("add", views.PersonCreateView.as_view(), name="create"),
    path("<int:pk>/modify", views.PersonUpdateView.as_view(), name="update"),
    path(
        "<int:pk>/toggle_active",
        views.PersonToggleActiveView.as_view(),
        name="toggle-active",
    ),
    path("<int:pk>/delete", views.PersonDeleteView.as_view(), name="delete"),
    path("<int:pk>/qualifications/qualify", views.QualifyPersonView.as_view(), name="qualify"),
    path(
        "<int:pk>/qualifications/<int:qualification>",
        views.EditQualificationPersonView.as_view(),
        name="edit-qualification",
    ),
    path(
        "<int:pk>/qualifications/revoke/<int:qualification>",
        views.RevokeQualificationPersonView.as_view(),
        name="revoke-qualification",
    ),
    path(
        "<int:pk>/qualifications",
        views.PersonQualificationsListView.as_view(),
        name="qualifications",
    ),
    path(
        "<int:pk>/instructor/add",
        views.AddInstructorPersonView.as_view(),
        name="add-instructor",
    ),
    path(
        "<int:pk>/instructor/revoke/<int:instructor>",
        views.RevokeInstructorPersonView.as_view(),
        name="revoke-instructor",
    ),
    path(
        "<int:pk>/instructor",
        views.PersonInstructorListView.as_view(),
        name="instructs-for",
    ),
    
    # AJAX calls
    path(
        "autocomplete/qualify/<int:machine>",
        ajax.QualifyablePersonAutocompleteView.as_view(),
        name="autocomplete-qualifyable",
    ),
    path(
        "autocomplete/instructor/<int:machine>",
        ajax.InstructorPersonAutocompleteView.as_view(),
        name="autocomplete-instructor",
    ),
]
