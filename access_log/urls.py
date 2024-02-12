from django.contrib import admin
from django.urls import path

app_name = 'access_log'

from . import views

urlpatterns = [
        path('', views.AccessLogListView.as_view(), name='list'),
        path('for_token/<int:token>', views.AccessLogForTokenSnippet.as_view(), name='for-token'),
]
