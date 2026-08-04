from django import template
from django.utils.translation import gettext_lazy as _
from django.utils import formats

from users.models import RFIDingUser
from base.app_icons import app_icon as _app_icon

register = template.Library()


@register.filter(name="app_icon")
def app_icon(app_name):
    return _app_icon(app_name)


@register.simple_tag
def get_verbose_name(object):
    if hasattr(object, "_meta"):
        return object._meta.verbose_name
    return object


@register.simple_tag
def get_verbose_name_plural(object):
    if hasattr(object, "_meta"):
        return object._meta.verbose_name_plural.capitalize()
    return object


@register.filter
def verbose_name(object):
    if hasattr(object, "_meta"):
        return object._meta.verbose_name
    return object.__class__.__name__


@register.filter
def verbose_name_plural(object):
    if hasattr(object, "_meta"):
        return object._meta.verbose_name_plural
    return object.__class__.__name__

@register.filter
def verbose_name_adaptive(object, count):
    if hasattr(object, "_meta"):
        if count == 1:
            return object._meta.verbose_name
        else:
            return object._meta.verbose_name_plural
    return object.__class__.__name__

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter("range")
def make_range(start, end):
    return range(start, end + 1)


@register.filter("range_excl")
def make_range_excl(start, end):
    return range(start, end)


@register.filter
def limit_to(value, arg):
    return value[:arg]


@register.filter
def limit_to_last(value, arg):
    return value[-arg:]


@register.simple_tag
def build_url_params(params, **kwargs):
    params = params.copy()
    for kwarg in kwargs:
        params[kwarg] = kwargs[kwarg]
    if len(params) == 0:
        return ""
    return "?" + "&".join([f"{k}={v}" for k, v in params.items()])


@register.filter(name="translate")
def translate(text):
    try:
        return _(text)
    except Exception:
        return text

@register.simple_tag(name="user_date", takes_context=True)
def user_date(context, date, format="DATE_FORMAT"):
    if date is None:
        return None
    if isinstance(date, str):
        return date
    if format in context:
        print("Cached format", context[format])
        return formats.date_format(date, context[format])
    add_time = False
    used_format = format
    if "DATETIME" in used_format:
        add_time = True
        used_format = used_format.replace("DATETIME", "DATE").strip()
    user = context["request"].user
    if user.date_format != RFIDingUser.DateFormat.LOCALE:
        date_format = user.date_format
    else:
        date_format = formats.get_format(used_format, lang=user.language)
    if add_time:
        if user.time_format == RFIDingUser.TimeFormat.H24:
            time_format = "H:i"
        elif user.time_format == RFIDingUser.TimeFormat.H12:
            time_format = "h:i A"
        else:
            time_format = formats.get_format("TIME_FORMAT", lang=user.language)
        date_format = f"{date_format} {time_format}"
    context[format] = date_format
    return formats.date_format(date, date_format)