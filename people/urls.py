from django.urls import path

from people.views import AssignQualificationView, PersonCreateView, PersonDetailView, PersonListView, PersonUpdateView, UnassignQualificationView

app_name = "people"
urlpatterns = [
    path("", PersonListView.as_view(), name="list"),
    path("<int:pk>/", PersonDetailView.as_view(), name="detail"),
    path("add/", PersonCreateView.as_view(), name="create"),
    path("<int:pk>/update", PersonUpdateView.as_view(), name="update"),
    path("assign/<int:person>/<int:machine>", AssignQualificationView.as_view(), name="assign_qualification"),
    path("unassign/<int:person>/<int:machine>", UnassignQualificationView.as_view(), name="unassign_qualification")
]