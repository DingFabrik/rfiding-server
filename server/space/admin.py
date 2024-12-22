from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import SpaceState

@admin.register(SpaceState)
class SpaceStateAdmin(admin.ModelAdmin):
    list_display = ["is_open", "created"]
    date_hierarchy = "created"