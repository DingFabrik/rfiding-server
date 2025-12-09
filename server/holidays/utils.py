from django.db.models import Q
from .models import Holiday

from django.utils import timezone

def get_holiday_by_date(date):
    try:
        return Holiday.objects.get(
            Q(repeats_annually=True, date__month=date.month, date__day=date.day)
            | Q(repeats_annually=False, date=date)
        )
    except Holiday.DoesNotExist:
        return None

def is_holiday(date):
    return get_holiday_by_date(date) is not None

def is_today_holiday(ignore_cache=False):
    today = timezone.localdate()
    if Holiday.cache["date"] == today and not ignore_cache:
        return Holiday.cache["holiday"] is not None
    Holiday.cache["date"] = today
    Holiday.cache["holiday"] = get_holiday_by_date(today)
    return Holiday.cache["holiday"] is not None