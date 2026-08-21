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

class ExpiredListFilter(admin.SimpleListFilter):
    title = _("Qualification Expired")
    parameter_name = "expired"

    def lookups(self, request, model_admin):
        return [
            ("yes", _("Yes")),
            ("no", _("No")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(expired__isnull=False)
        if self.value() == "no":
            return queryset.filter(expired__isnull=True)


class QualificationAdmin(admin.ModelAdmin):
    search_fields = ("person__name", "machine__name", "machine__hostname")
    list_display = ("person", "machine", "permission_level", "is_instructor", "is_maintainer", "last_used", "expired")
    list_filter = (ExpiredListFilter, "permission_level", "is_instructor", "is_maintainer")
    
    actions = [mark_expired, mark_unexpired]

admin.site.register(Person, PersonAdmin)
admin.site.register(Qualification, QualificationAdmin)
