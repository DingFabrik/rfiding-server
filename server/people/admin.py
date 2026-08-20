from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Person, Qualification
from base.admin import mark_active, mark_inactive
from .conf import PERSON_ENABLE_SLACK_EMAIL, PERSON_ENABLE_EMAIL


class PersonAdmin(admin.ModelAdmin):
    list_display = ("member_id", "name", "email", "is_system_maintainer", "is_active")
    search_fields = ("name", "email")
    list_filter = ("is_active", "language", "is_system_maintainer")

    actions = [mark_active, mark_inactive]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude = []
        if not PERSON_ENABLE_SLACK_EMAIL:
            self.exclude.append("slack_email")
            self.exclude.append("slack_conversation_id")
        if not PERSON_ENABLE_EMAIL:
            self.exclude.append("email")

@admin.action(description=_("Mark selected qualifications as expired"))
def mark_expired(modeladmin, request, queryset):
    queryset.update(expired=timezone.now(), expires_at=timezone.now())
    
@admin.action(description=_("Mark selected qualifications as unexpired"))
def mark_unexpired(modeladmin, request, queryset):
    queryset.update(expired=None, expires_at=None)

class QualificationAdmin(admin.ModelAdmin):
    list_display = ("person", "machine", "last_used", "expires_at", "expired", "notified_at")
    list_filter = ("expired",)
    
    actions = [mark_expired, mark_unexpired]

admin.site.register(Person, PersonAdmin)
admin.site.register(Qualification, QualificationAdmin)
