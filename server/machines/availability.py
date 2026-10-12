"""Whether a machine can be used right now, and its weekly usage times, for the
public machine page."""

from dataclasses import dataclass

from django.conf import settings
from django.utils import dateformat, formats, timezone
from django.utils.translation import gettext as _

from holidays.utils import is_today_holiday
from .models import Machine

SHORT_DAY_NAMES = (
    lambda: _("Mon"),
    lambda: _("Tue"),
    lambda: _("Wed"),
    lambda: _("Thu"),
    lambda: _("Fri"),
    lambda: _("Sat"),
    lambda: _("Sun"),
)


def _format_time(value):
    # The project's 24-hour TIME_FORMAT, not the locale's "10 p.m."
    return dateformat.time_format(value, settings.TIME_FORMAT)


def _format_range(start, end):
    return f"{_format_time(start)} – {_format_time(end)}"


@dataclass
class Availability:
    # "usable", "closed", "maintenance" or "inactive"
    status: str
    headline: str
    detail: str = ""
    message: str = ""


@dataclass
class UsageRow:
    label: str
    hours: str
    is_today: bool = False


def _ranges_by_weekday(times):
    days = {day: [] for day in range(7)}
    for time in times:
        for day in time.weekdays or range(7):
            days[day].append((time.start_time, time.end_time))
    for ranges in days.values():
        ranges.sort()
    return days


def get_usage_rows(machine, now=None):
    """Weekly usage times, consecutive days with the same hours grouped, today
    split into its own row."""
    times = list(machine.times.all())
    if not times:
        return []
    now = now or timezone.localtime()
    today = now.weekday()
    by_day = _ranges_by_weekday(times)

    groups = []
    for day in range(7):
        key = tuple(by_day[day])
        last = groups[-1] if groups else None
        if (
            last is not None
            and last["key"] == key
            and today not in (day, last["days"][-1])
        ):
            last["days"].append(day)
        else:
            groups.append({"key": key, "days": [day]})

    rows = []
    for group in groups:
        first, last = group["days"][0], group["days"][-1]
        label = SHORT_DAY_NAMES[first]()
        if last != first:
            label = f"{label} – {SHORT_DAY_NAMES[last]()}"
        is_today = first == today
        if is_today:
            label = f"{label} · {_('today')}"
        if group["key"]:
            hours = ", ".join(_format_range(start, end) for start, end in group["key"])
        else:
            hours = _("Not usable")
        rows.append(UsageRow(label, hours, is_today))
    return rows


def _next_opening(by_day, now):
    for offset in range(8):
        day = (now.weekday() + offset) % 7
        for start, _end in by_day[day]:
            if offset == 0 and start <= now.time():
                continue
            return offset, day, start
    return None


def _today_hours(by_day, now):
    ranges = by_day[now.weekday()]
    return ", ".join(_format_range(start, end) for start, end in ranges)


def get_availability(machine, now=None):
    now = now or timezone.localtime()
    times = list(machine.times.all())
    by_day = _ranges_by_weekday(times)
    today_hours = _today_hours(by_day, now) if times else ""

    if machine.state == Machine.MachineStatus.MAINTENANCE:
        detail = _("Not usable right now.")
        if today_hours:
            detail = _("Not usable right now. Normally usable today %(hours)s.") % {
                "hours": today_hours
            }
        return Availability(
            "maintenance",
            _("In maintenance"),
            detail,
            machine.maintenance_message or "",
        )
    if machine.state == Machine.MachineStatus.INACTIVE:
        return Availability(
            "inactive", _("Not in service"), _("This machine is currently disabled.")
        )
    if not machine.allowed_on_holidays and is_today_holiday():
        return Availability(
            "closed",
            _("Not usable today"),
            _("Today is a holiday, and this machine can't be used on holidays."),
        )

    if not times:
        return Availability("usable", _("Usable now"), _("No restricted usage times."))

    current = [
        end for start, end in by_day[now.weekday()] if start <= now.time() <= end
    ]
    if current:
        return Availability(
            "usable",
            _("Usable now – until %(time)s") % {"time": _format_time(max(current))},
        )

    opening = _next_opening(by_day, now)
    if opening is None:
        return Availability("closed", _("Not usable right now"))
    offset, day, start = opening
    if offset == 0:
        when = _("today at %(time)s")
    elif offset == 1:
        when = _("tomorrow at %(time)s")
    else:
        when = _("%(day)s at %(time)s")
    when = when % {"day": SHORT_DAY_NAMES[day](), "time": _format_time(start)}
    return Availability(
        "closed",
        _("Not usable right now"),
        _("Next usable %(when)s.") % {"when": when},
    )


def weekday_name(now=None):
    now = now or timezone.localtime()
    return formats.date_format(now, "l")
