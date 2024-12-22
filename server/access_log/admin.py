from django.contrib import admin

from .models import AccessLog

@admin.action(description="Mark setup as completed")
def complete_setup(modeladmin, request, queryset):
    queryset.update(completed_setup=True)

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "token", "machine", "type")
    date_hierarchy = "timestamp"
    
    list_filter = ("type",)
