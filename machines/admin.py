from django.contrib import admin

from machines.models import Machine

class MachineAdmin(admin.ModelAdmin):
    pass


admin.site.register(Machine, MachineAdmin)