from django.contrib import admin

from .models import SpaceState

@admin.register(SpaceState)
class SpaceStateAdmin(admin.ModelAdmin):
    list_display = ["is_open", "created"]
    date_hierarchy = "created"