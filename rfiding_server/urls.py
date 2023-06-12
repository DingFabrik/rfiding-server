"""rfiding_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from base.views import InitialSetupView
from machines.views import MachineListView
from machines.viewsets import RetrieveMachineConfigAPIView
from people.views import PersonListView
from tokens.views import TokenListView

from users.views import HomeView, RfiDingLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('setup', InitialSetupView.as_view(), name='initial-setup'),
    path('', HomeView.as_view(), name='home_view'),
    path("auth/login/", RfiDingLoginView.as_view(), name='login'),

    path("machines/", include("machines.urls", namespace="machines")),
    path("people/", include("people.urls", namespace="people")),
    path("tokens/", include("tokens.urls", namespace="tokens")),

    path("api/machine/config", RetrieveMachineConfigAPIView.as_view(), name="api-machine-config"),
    path("api/machine/check", RetrieveMachineConfigAPIView.as_view(), name="api-machine-check")
]
