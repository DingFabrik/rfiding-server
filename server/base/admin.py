from django.contrib import admin
from django.utils.translation import gettext_lazy as _

@admin.action(description=_("Mark selected items as active"))
def mark_active(modeladmin, request, queryset):
    queryset.update(is_active=True)
    
@admin.action(description=_("Mark selected items as inactive"))
def mark_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)