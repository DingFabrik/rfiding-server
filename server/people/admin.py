from django.contrib import admin

from .models import Person, Qualification
from base.admin import mark_active, mark_inactive


class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    search_fields = ("name", "email")
    list_filter = ("is_active",)

    actions = [mark_active, mark_inactive]


class QualificationAdmin(admin.ModelAdmin):
    list_display = ("person", "machine", "last_used", "expires_at", "expired", "notified_at")
    list_filter = ("expired",)

admin.site.register(Person, PersonAdmin)
admin.site.register(Qualification, QualificationAdmin)
