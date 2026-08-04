from django import template

from users.models import UserWidget

register = template.Library()


@register.filter
def widget_icon(widget_type):
    return UserWidget(widget=widget_type).icon
