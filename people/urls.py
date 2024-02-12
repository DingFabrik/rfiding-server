from django.contrib import admin
from django.urls import path

from . import views

app_name = 'people'

urlpatterns = [
    path('', views.PersonListView.as_view(), name='list'),
    path('<int:pk>', views.PersonDetailView.as_view(), name='detail'),
    path('add', views.PersonCreateView.as_view(), name='create'),
    path('<int:pk>/modify', views.PersonUpdateView.as_view(), name='update'),
    path('<int:pk>/toggle_active', views.PersonToggleActiveView.as_view(), name='toggle-active'),
    path('<int:pk>/delete', views.PersonDeleteView.as_view(), name='delete'),
    path('<int:pk>/qualify', views.QualifyPersonView.as_view(), name='qualify'),
    path('<int:pk>/revoke/<int:qualification>', views.RevokeQualificationPersonView.as_view(), name='revoke-qualification'),
    path('<int:pk>/add-instructor', views.AddInstructorPersonView.as_view(), name='add-instructor'),
    path('<int:pk>/revoke-instructor/<int:instructor>', views.RevokeInstructorPersonView.as_view(), name='revoke-instructor'),
]
