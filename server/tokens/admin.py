from django.contrib import admin

from .models import Token, TokenType, UnknownToken
from base.admin import mark_active, mark_inactive

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ["serial", "is_active", "type", "created"]
    search_fields = ["serial", "type"]
    list_filter = ["is_active", "type"]
    
    actions = [mark_active, mark_inactive]
    
@admin.register(TokenType)
class TokenTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "label_prefix"]
    search_fields = ["name", "label_prefix"]

admin.site.register(UnknownToken)