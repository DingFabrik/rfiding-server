from django.contrib import admin
from django.urls import path

app_name = 'firmware'

from . import views

urlpatterns = [
    path('', views.FirmwareListView.as_view(), name='list'),
    path('update', views.FirmwareUpdateView.as_view(), name='update'),
    path('create', views.FirmwareCreateView.as_view(), name='create'),
    path('<int:pk>/delete', views.FirmwareDeleteView.as_view(), name='delete'),
    path('<int:pk>', views.FirmwareDetailView.as_view(), name='detail'),
]
