from django.contrib import admin

from .models import AccessLog


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "token", "machine", "type", "unsuccessful_reason")
    date_hierarchy = "timestamp"

    list_filter = ("type", "unsuccessful_reason")
