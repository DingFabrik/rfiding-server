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
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView

from base.views import AboutView, AuditlogView
from users.views import HomeView
from machines.api.v1 import CheckMachineAccessView, MachineConfigView
from space.api import APISpaceStatusView

api_v1_urls = [
    path("machine/check", CheckMachineAccessView.as_view(), name="machine_check"),
    path("machine/config", MachineConfigView.as_view(), name="machine_config"),
    path("space/status", APISpaceStatusView.as_view(), name="space_status"),
]

api_v2_urls = [
    path("machine/check", CheckMachineAccessView.as_view(), name="machine_check"),
    path("machine/config", MachineConfigView.as_view(), name="machine_config"),
    path("space/status", APISpaceStatusView.as_view(), name="space_status"),
]

api_urls = api_v1_urls + [
    path("v1/", include((api_v1_urls, "v1"), namespace="v1")),
    path("v2/", include((api_v2_urls, "v2"), namespace="v2")),
]

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/change-password/", PasswordChangeView.as_view(), name="password_change"),
    path("accounts/change-password-done/", PasswordChangeDoneView.as_view(), name="password_change_done"),
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
    path("auditlog/", AuditlogView.as_view(), name="auditlog"),
]
