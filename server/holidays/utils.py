from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from .models import Holiday

IS_TODAY_HOLIDAY_TIMEOUT = 60 * 60 * 25


def is_today_holiday_cache_key(date):
    return f"holidays:is_today_holiday:{date.isoformat()}"


def get_holiday_by_date(date):
    return Holiday.objects.filter(
        Q(repeats_annually=True, date__month=date.month, date__day=date.day)
        | Q(repeats_annually=False, date=date)
    ).first()


def is_holiday(date):
    return get_holiday_by_date(date) is not None


def is_today_holiday(ignore_cache=False):
    today = timezone.localdate()
    key = is_today_holiday_cache_key(today)
    if not ignore_cache:
        cached = cache.get(key)
        if cached is not None:
            return cached
    result = is_holiday(today)
    cache.set(key, result, IS_TODAY_HOLIDAY_TIMEOUT)
    return result