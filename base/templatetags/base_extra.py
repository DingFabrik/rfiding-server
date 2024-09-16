from django import template


register = template.Library()


@register.simple_tag
def get_verbose_name(object):
    return object._meta.verbose_name


@register.simple_tag
def get_verbose_name_plural(object):
    return object._meta.verbose_name_plural


@register.filter
def verbose_name(object):
    return object._meta.verbose_name


@register.filter
def verbose_name_plural(object):
    return object._meta.verbose_name_plural


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
