from django.contrib import admin
from django.urls import path

from . import views

app_name = 'space'

urlpatterns = [
    path('status', views.ShowSpaceStatus.as_view(), name='sstatus'),
]
