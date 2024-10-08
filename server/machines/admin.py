from django.contrib import admin

from .models import Machine, MachineTime

@admin.action(description="Mark setup as completed")
def complete_setup(modeladmin, request, queryset):
    queryset.update(completed_setup=True)

class MachineAdmin(admin.ModelAdmin):
    list_display = ("name", "hostname", "is_active", "completed_setup", "chip")
    search_fields = ("name", "hostname")
    
    actions = [complete_setup]


class MachineTimeAdmin(admin.ModelAdmin):
    pass


admin.site.register(Machine, MachineAdmin)
admin.site.register(MachineTime, MachineTimeAdmin)
