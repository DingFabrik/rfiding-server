from django.contrib import admin

from .models import Machine, MachineTime, MachineControlKey, MachineConnection
from base.admin import mark_active, mark_inactive


class MachineAdmin(admin.ModelAdmin):
    list_display = ("name", "hostname", "state", "chip")
    search_fields = ("name", "hostname")
    list_filter = ("state", "chip")

    actions = [mark_active, mark_inactive]


class MachineTimeAdmin(admin.ModelAdmin):
    pass

class MachineControlKeyAdmin(admin.ModelAdmin):
    pass

class MachineConnectionAdmin(admin.ModelAdmin):
    pass

admin.site.register(Machine, MachineAdmin)
admin.site.register(MachineTime, MachineTimeAdmin)
admin.site.register(MachineControlKey, MachineControlKeyAdmin)
admin.site.register(MachineConnection, MachineConnectionAdmin)