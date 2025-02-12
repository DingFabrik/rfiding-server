from django.contrib import admin

from .models import Machine, MachineTime
from base.admin import mark_active, mark_inactive

class MachineAdmin(admin.ModelAdmin):
    list_display = ("name", "hostname", "is_active", "chip")
    search_fields = ("name", "hostname")
    list_filter = ("is_active", "chip")
    
    actions = [mark_active, mark_inactive]


class MachineTimeAdmin(admin.ModelAdmin):
    pass


admin.site.register(Machine, MachineAdmin)
admin.site.register(MachineTime, MachineTimeAdmin)
