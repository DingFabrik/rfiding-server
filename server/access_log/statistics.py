from bisect import bisect_right
from datetime import datetime, time, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay, TruncDay
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from access_log.models import (
    AccessLog,
    LOG_TYPE_DISABLED,
    LOG_TYPE_ENABLED,
    LOG_TYPE_UNSUCCESSFUL,
)
from machines.models import Machine
from people.models import Qualification
from space.models import SpaceState

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
DEFAULT_DAYS = 90
TOP_COUNT = 10
EXPIRING_SOON_DAYS = 30

ENABLED = Q(type=LOG_TYPE_ENABLED)
DISABLED = Q(type=LOG_TYPE_DISABLED)
UNSUCCESSFUL = Q(type=LOG_TYPE_UNSUCCESSFUL)


def parse_days(value):
    """`value` as one of DAYS_CHOICES, falling back to DEFAULT_DAYS."""
    try:
        days = int(value)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return days if days in dict(DAYS_CHOICES) else DEFAULT_DAYS


def _hours(duration):
    return duration.total_seconds() / 3600 if duration else 0


def compute_access_breakdown(queryset, days):
    """Counts of `queryset` over the last `days` days, by day/hour/weekday."""
    query = queryset.filter(timestamp__gte=timezone.now() - timedelta(days=days))

    day_map = {
        row["day"].date(): row["count"]
        for row in query.annotate(day=TruncDay("timestamp"))
        .values("day")
        .annotate(count=Count("id"))
    }
    today = timezone.localdate()
    access_by_day = []
    for offset in range(days - 1, -1, -1):
        date = today - timedelta(days=offset)
        access_by_day.append(
            {"day": date.strftime("%d.%m"), "count": day_map.get(date, 0)}
        )

    hour_map = {
        row["hour"]: row["count"]
        for row in query.annotate(hour=ExtractHour("timestamp"))
        .values("hour")
        .annotate(count=Count("id"))
    }
    access_by_hour = [
        {"hour": hour, "count": hour_map.get(hour, 0)} for hour in range(24)
    ]

    weekday_map = {
        row["weekday"]: row["count"]
        for row in query.annotate(weekday=ExtractIsoWeekDay("timestamp"))
        .values("weekday")
        .annotate(count=Count("id"))
    }
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


def compute_unused_qualifications(timeframe_start):
    """Active qualifications held since before `timeframe_start` but not used since."""
    held = Qualification.objects.filter(
        expired__isnull=True, person__is_active=True, created__lt=timeframe_start
    ).exclude(machine__state=Machine.MachineStatus.INACTIVE)
    unused = Q(last_used__isnull=True) | Q(last_used__lt=timeframe_start)
    totals = held.aggregate(qualified=Count("id"), unused=Count("id", filter=unused))
    machines = list(
        held.values("machine", "machine__name")
        .annotate(qualified=Count("id"), unused=Count("id", filter=unused))
        .filter(unused__gt=0)
        .order_by("-unused", "machine__name")[:TOP_COUNT]
    )
    for row in machines:
        row["unused_percent"] = row["unused"] / row["qualified"] * 100
    return {
        "qualified_total": totals["qualified"],
        "unused_total": totals["unused"],
        "machines": machines,
    }


def get_space_open_intervals(start, end):
    """(opened, closed) intervals within start..end, or None without any space state."""
    prior = SpaceState.objects.filter(created__lt=start).order_by("-created").first()
    states = list(
        SpaceState.objects.filter(created__gte=start, created__lt=end).order_by("created")
    )
    if prior is None and not states:
        return None
    intervals = []
    open_since = start if prior is not None and prior.is_open else None
    for state in states:
        if state.is_open and open_since is None:
            open_since = state.created
        elif not state.is_open and open_since is not None:
            intervals.append((open_since, state.created))
            open_since = None
    if open_since is not None:
        intervals.append((open_since, end))
    return intervals


def _seconds_by_day(intervals):
    tz = timezone.get_current_timezone()
    seconds = {}
    for start, end in intervals:
        day = timezone.localtime(start).date()
        while True:
            day_start = datetime.combine(day, time.min, tzinfo=tz)
            day_end = day_start + timedelta(days=1)
            overlap = (min(end, day_end) - max(start, day_start)).total_seconds()
            if overlap <= 0:
                break
            seconds[day] = seconds.get(day, 0) + overlap
            day += timedelta(days=1)
    return seconds


def compute_space_usage(logs, timeframe_start, days):
    """How machine usage relates to the hours the space was open."""
    now = timezone.now()
    intervals = get_space_open_intervals(timeframe_start, now)
    if intervals is None:
        return None
    open_hours = sum((end - start).total_seconds() for start, end in intervals) / 3600

    starts = [start for start, _ in intervals]
    accesses_open = accesses_closed = 0
    for timestamp in logs.filter(ENABLED).values_list("timestamp", flat=True):
        index = bisect_right(starts, timestamp) - 1
        if index >= 0 and timestamp < intervals[index][1]:
            accesses_open += 1
        else:
            accesses_closed += 1
    accesses = accesses_open + accesses_closed

    usage_by_day = {
        row["day"].date(): _hours(row["usage"])
        for row in logs.filter(DISABLED)
        .annotate(day=TruncDay("timestamp"))
        .values("day")
        .annotate(usage=Sum("enabled_duration"))
    }
    open_by_day = _seconds_by_day(intervals)
    today = timezone.localdate()
    by_day = []
    for offset in range(days - 1, -1, -1):
        date = today - timedelta(days=offset)
        by_day.append(
            {
                "day": date.strftime("%d.%m"),
                "open_hours": round(open_by_day.get(date, 0) / 3600, 1),
                "usage_hours": round(usage_by_day.get(date, 0), 1),
            }
        )

    return {
        "open_hours": open_hours,
        "accesses_closed": accesses_closed,
        "closed_percent": accesses_closed / accesses * 100 if accesses else 0,
        "machines_running": sum(usage_by_day.values()) / open_hours if open_hours else 0,
        "by_day": by_day,
    }


def compute_global_statistics(days=DEFAULT_DAYS):
    """Usage statistics across all machines and people for the last `days` days."""
    timeframe_start = timezone.now() - timedelta(days=days)
    logs = AccessLog.objects.filter(timestamp__gte=timeframe_start)

    totals = logs.aggregate(
        accesses=Count("id", filter=ENABLED),
        unsuccessful=Count("id", filter=UNSUCCESSFUL),
        active_people=Count("token__person", filter=ENABLED, distinct=True),
        active_machines=Count("machine", filter=ENABLED, distinct=True),
        usage=Sum("enabled_duration", filter=DISABLED),
    )
    previous_accesses = AccessLog.objects.filter(
        ENABLED,
        timestamp__gte=timeframe_start - timedelta(days=days),
        timestamp__lt=timeframe_start,
    ).count()
    if previous_accesses:
        access_change = (totals["accesses"] - previous_accesses) / previous_accesses * 100
    else:
        access_change = None

    top_machines = list(
        logs.values("machine", "machine__name")
        .annotate(
            accesses=Count("id", filter=ENABLED),
            unsuccessful=Count("id", filter=UNSUCCESSFUL),
            people=Count("token__person", filter=ENABLED, distinct=True),
            usage=Sum("enabled_duration", filter=DISABLED),
        )
        .filter(accesses__gt=0)
        .order_by("-accesses", "machine__name")[:TOP_COUNT]
    )
    top_people = list(
        logs.filter(token__person__isnull=False)
        .values("token__person", "token__person__name")
        .annotate(
            accesses=Count("id", filter=ENABLED),
            machines=Count("machine", filter=ENABLED, distinct=True),
            usage=Sum("enabled_duration", filter=DISABLED),
        )
        .filter(accesses__gt=0)
        .order_by("-accesses", "token__person__name")[:TOP_COUNT]
    )
    for row in top_machines + top_people:
        row["usage_hours"] = _hours(row["usage"])

    idle_machines = (
        Machine.objects.filter(state=Machine.MachineStatus.ACTIVE)
        .exclude(pk__in=logs.filter(ENABLED).values("machine"))
        .order_by("name")
    )

    now = timezone.now()
    expiring = Qualification.objects.filter(
        expired__isnull=True,
        person__is_active=True,
        expires_at__gte=now,
        expires_at__lt=now + timedelta(days=EXPIRING_SOON_DAYS),
    ).select_related("person", "machine").order_by("expires_at")

    statistics = compute_access_breakdown(logs.filter(ENABLED), days)
    statistics.update(
        {
            "total_accesses": totals["accesses"],
            "access_change": access_change,
            "unsuccessful_attempts": totals["unsuccessful"],
            "active_people": totals["active_people"],
            "active_machines": totals["active_machines"],
            "usage_hours": _hours(totals["usage"]),
            "qualifications_granted": Qualification.objects.filter(
                created__gte=timeframe_start
            ).count(),
            "qualifications_expired": Qualification.objects.filter(
                expired__gte=timeframe_start
            ).count(),
            "top_machines": top_machines,
            "top_people": top_people,
            "idle_machine_count": idle_machines.count(),
            "idle_machines": idle_machines[:TOP_COUNT],
            "unused_qualifications": compute_unused_qualifications(timeframe_start),
            "expiring_soon_days": EXPIRING_SOON_DAYS,
            "expiring_qualification_count": expiring.count(),
            "expiring_qualifications": expiring[:TOP_COUNT],
            "space_usage": compute_space_usage(logs, timeframe_start, days),
        }
    )
    return statistics
