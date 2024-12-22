from django.contrib import admin

@admin.action(description="Mark selected items as active")
def mark_active(modeladmin, request, queryset):
    queryset.update(is_active=True)
    
@admin.action(description="Mark selected items as inactive")
def mark_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)