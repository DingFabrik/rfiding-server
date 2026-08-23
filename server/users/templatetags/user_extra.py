from django import template
from django.utils.safestring import mark_safe

from users.models import RFIDingUser, UserWidget
from users.theming import theme_css_declarations, theme_name

register = template.Library()


@register.filter
def widget_icon(widget_type):
    return UserWidget(widget=widget_type).icon


def _effective_theme_settings(user):
    if not getattr(user, "is_authenticated", False):
        return RFIDingUser.ThemeMode.SYSTEM, "default", "default"
    return user.theme_mode, user.light_theme, user.dark_theme


@register.simple_tag
def theme_html_attrs(user):
    """The data-theme attribute for <html>, resolved without any JavaScript.

    "system" mode renders the light theme here (for browsers/crawlers that
    ignore the accompanying prefers-color-scheme override) - see
    theme_style_block for the dark override.
    """
    mode, light_theme, dark_theme = _effective_theme_settings(user)
    if mode == RFIDingUser.ThemeMode.DARK:
        name = theme_name(dark_theme, "dark")
    else:
        name = theme_name(light_theme, "light")
    return mark_safe(f'data-theme="{name}"')


@register.simple_tag
def theme_style_block(user):
    """A prefers-color-scheme override so "system" mode needs no JavaScript."""
    mode, light_theme, dark_theme = _effective_theme_settings(user)
    if mode != RFIDingUser.ThemeMode.SYSTEM:
        return ""
    light_name = theme_name(light_theme, "light")
    declarations = "\n      ".join(theme_css_declarations(dark_theme, "dark"))
    css = (
        "@media (prefers-color-scheme: dark) {\n"
        f'  html[data-theme="{light_name}"] {{\n'
        f"      {declarations}\n"
        "  }\n"
        "}"
    )
    return mark_safe(f"<style>{css}</style>")
