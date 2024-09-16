"""
URL configuration for rfiding project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.urls import path, include

from base.views import AboutView
from users.views import HomeView
from machines.api import CheckMachineAccessView, MachineConfigView
from space.api import APISpaceStatusView

api_urls = [
    path("machine/check", CheckMachineAccessView.as_view(), name="machine_check"),
    path("machine/config", MachineConfigView.as_view(), name="machine_config"),
    path("space/status", APISpaceStatusView.as_view(), name="space_status"),
]

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("access_log/", include("access_log.urls", namespace="access_log")),
    path("machines/", include("machines.urls", namespace="machines")),
    path("people/", include("people.urls", namespace="people")),
    path("space/", include("space.urls", namespace="space")),
    path("tokens/", include("tokens.urls", namespace="tokens")),
    path("users/", include("users.urls", namespace="users")),
    path("firmware/", include("firmware.urls", namespace="firmware")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("api/", include((api_urls, "api"), namespace="api")),
    path("about/", AboutView.as_view(), name="about"),
]
