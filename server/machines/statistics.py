from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncHour, ExtractWeekDay

from access_log.models import AccessLog, LOG_TYPE_ENABLED

WEEKDAYS = [
    _("Monday"),
    _("Tuesday"),
    _("Wednesday"),
    _("Thursday"),
    _("Friday"),
    _("Saturday"),
    _("Sunday"),
]

DAYS_CHOICES = [
    (7, _("7 Days")),
    (30, _("30 Days")),
    (90, _("90 Days")),
    (365, _("365 Days")),
]


def compute_machine_statistics(machine, days=90):
    """Access counts for `machine` over the last `days` days, by day/hour/weekday."""
    timeframe_start = timezone.now() - timedelta(days=days)
    query = AccessLog.objects.filter(
        machine=machine, timestamp__gte=timeframe_start, type=LOG_TYPE_ENABLED
    )

    day_counts = (
        query.annotate(day=TruncDay("timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .all()
    )
    day_map = {}
    for count in day_counts:
        day_map[count["day"].strftime("%d.%m")] = count["count"]
    today = timezone.localdate()
    access_by_day = []
    for day in range(days):
        date = (today - timedelta(days=days - 1 - day)).strftime("%d.%m")
        access_by_day.append({"day": date, "count": day_map.get(date, 0)})

    hour_map = {}
    counts = (
        query.annotate(hour=TruncHour("timestamp"))
        .values("hour")
        .annotate(count=Count("id"))
        .all()
    )
    for count in counts:
        hour_map[count["hour"].hour] = count["count"]
    access_by_hour = [
        {"hour": hour, "count": hour_map.get(hour, 0)} for hour in range(24)
    ]

    weekday_map = {}
    counts = (
        query.annotate(weekday=ExtractWeekDay("timestamp"))
        .values("weekday")
        .annotate(count=Count("id"))
        .all()
    )
    for count in counts:
        index = count["weekday"] - 1
        if index == 0:
            index = 7
        weekday_map[index] = count["count"]
    access_by_weekday = [
        {"weekday": WEEKDAYS[weekday - 1], "count": weekday_map.get(weekday, 0)}
        for weekday in range(1, 8)
    ]

    return {
        "access_by_day": access_by_day,
        "access_by_hour": access_by_hour,
        "access_by_weekday": access_by_weekday,
        "selected_days": days,
        "days_choices": DAYS_CHOICES,
    }
