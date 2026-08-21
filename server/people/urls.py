from django.urls import path

from . import views
from . import ajax

app_name = "people"

urlpatterns = [
    path(
        "view/<str:key>",
        views.PersonPublicDetailView.as_view(),
        name="public-detail",
    ),
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
    path(
        "<int:pk>/qualifications/qualify",
        views.QualifyPersonView.as_view(),
        name="qualify",
    ),
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
    # AJAX calls
    path(
        "autocomplete/person",
        ajax.PersonAutocompleteView.as_view(),
        name="autocomplete",
    ),
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
    path(
        "person-popover",
        views.PersonPopoverView.as_view(),
        name="person-popover",
    ),
    path(
        "<int:pk>/comments/add",
        views.PersonCommentCreateView.as_view(),
        name="add-comment",
    ),
]
