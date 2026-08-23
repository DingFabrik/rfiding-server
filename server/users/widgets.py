from datetime import datetime, time, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils import timezone
from auditlog.models import LogEntry

from people.models import Person
from tokens.models import Token
from machines.models import Machine, MachineRegistrationRequest
from access_log.models import AccessLog, LOG_TYPE_ENABLED
from space.models import SpaceState

SPACE_HEATMAP_WEEKS = 12


def _split_seconds_by_day(start, end):
    tz = start.tzinfo
    day = start.date()
    while day <= end.date():
        day_start = datetime.combine(day, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        overlap_start = max(start, day_start)
        overlap_end = min(end, day_end)
        if overlap_end > overlap_start:
            yield day, (overlap_end - overlap_start).total_seconds()
        day += timedelta(days=1)


class WidgetDataProvider():
    def __init__(self):
        self.data = {}

    def prepare_token_counts(self):
        if "activeTokenCount" not in self.data:
            self.data["activeTokenCount"] = Token.objects.filter(is_active=True).count()
        if "tokenCount" not in self.data:
            self.data["tokenCount"] = Token.objects.count()

    def prepare_machine_counts(self):
        if "activeMachineCount" not in self.data:
            self.data["activeMachineCount"] = Machine.objects.filter(state="active").count()
        if "maintenanceMachineCount" not in self.data:
            self.data["maintenanceMachineCount"] = Machine.objects.filter(state="maintenance").count()
        if "machineCount" not in self.data:
            self.data["machineCount"] = Machine.objects.count()

    def prepare_person_counts(self):
        if "activePeopleCount" not in self.data:
            self.data["activePeopleCount"] = Person.objects.filter(is_active=True).count()
        if "peopleCount" not in self.data:
            self.data["peopleCount"] = Person.objects.count()

    def prepare_access_log_latest(self):
        if "latestAccessLog" not in self.data:
            self.data["latestAccessLog"] = AccessLog.objects.select_related(
                "machine", "token"
            ).all()

    def prepare_access_log_chart(self):
        if "accessLogByDay" not in self.data:
            days = 14
            timeframe_start = timezone.now() - timedelta(days=days)
            day_counts = (
                AccessLog.objects.filter(
                    timestamp__gte=timeframe_start, type=LOG_TYPE_ENABLED
                )
                .annotate(day=TruncDay("timestamp"))
                .values("day")
                .annotate(count=Count("id"))
            )
            day_map = {c["day"].strftime("%d.%m"): c["count"] for c in day_counts}
            today = timezone.localdate()
            day_list = []
            for day in range(days):
                date = (today - timedelta(days=days - 1 - day)).strftime("%d.%m")
                day_list.append({"day": date, "count": day_map.get(date, 0)})
            self.data["accessLogByDay"] = day_list

    def prepare_audit_log_latest(self):
        if "latestAuditLog" not in self.data:
            self.data["latestAuditLog"] = LogEntry.objects.select_related(
                "content_type", "actor"
            ).order_by("-timestamp")

    def prepare_pending_registration_requests(self):
        if "pendingRegistrationRequests" not in self.data:
            self.data["pendingRegistrationRequests"] = (
                MachineRegistrationRequest.objects.order_by("-created")
            )

    def prepare_space_status(self):
        if "spaceHeatmapWeeks" in self.data:
            return
        today = timezone.localdate()
        current_week_start = today - timedelta(days=today.weekday())
        start_date = current_week_start - timedelta(weeks=SPACE_HEATMAP_WEEKS - 1)
        end_date = current_week_start + timedelta(days=6)
        tz = timezone.get_current_timezone()
        window_start = datetime.combine(start_date, time.min, tzinfo=tz)

        prior_entry = (
            SpaceState.objects.filter(created__lt=window_start)
            .order_by("-created")
            .first()
        )
        entries = list(
            SpaceState.objects.filter(created__gte=window_start).order_by("created")
        )

        day_seconds = {}

        def record(start, end):
            for day, seconds in _split_seconds_by_day(start, end):
                if start_date <= day <= end_date:
                    day_seconds[day] = day_seconds.get(day, 0) + seconds

        open_since = window_start if prior_entry is not None and prior_entry.is_open else None
        for entry in entries:
            if entry.is_open:
                open_since = entry.created
            elif open_since is not None:
                record(open_since, entry.created)
                open_since = None
        if open_since is not None:
            record(open_since, timezone.now())

        max_hours = max(day_seconds.values(), default=0) / 3600

        weeks = []
        week = []
        day = start_date
        while day <= end_date:
            if day > today:
                week.append(None)
            else:
                hours = day_seconds.get(day, 0) / 3600
                ratio = hours / max_hours if max_hours > 0 else 0
                if hours <= 0:
                    level = 0
                elif ratio <= 0.2:
                    level = 1
                elif ratio <= 0.4:
                    level = 2
                elif ratio <= 0.6:
                    level = 3
                elif ratio <= 0.8:
                    level = 4
                else:
                    level = 5
                week.append({"date": day, "hours": hours, "level": level})
            if len(week) == 7:
                weeks.append(week)
                week = []
            day += timedelta(days=1)

        self.data["spaceHeatmapWeeks"] = weeks
        self.data["spaceState"] = SpaceState.objects.first()

    def prepare_machines_maintenance(self):
        if "maintenanceMachines" not in self.data:
            self.data["maintenanceMachines"] = Machine.objects.filter(
                state="maintenance"
            ).select_related("location")

    def provide_for_widgets(self, widgets):
        for widget in widgets:
            if widget.widget == "token_counts":
                self.prepare_token_counts()
                widget.data = {
                    "active_count": self.data["activeTokenCount"],
                    "total_count": self.data["tokenCount"]
                }
            elif widget.widget == "machine_counts":
                self.prepare_machine_counts()
                widget.data = {
                    "active_count": self.data["activeMachineCount"],
                    "maintenance_count": self.data["maintenanceMachineCount"],
                    "total_count": self.data["machineCount"]
                }
            elif widget.widget == "people_counts":
                self.prepare_person_counts()
                widget.data = {
                    "active_count": self.data["activePeopleCount"],
                    "total_count": self.data["peopleCount"]
                }
            elif widget.widget == "access_log_latest":
                self.prepare_access_log_latest()
                widget.data = {
                    "log_entries": self.data["latestAccessLog"][:10]
                }
            elif widget.widget == "access_log_chart":
                self.prepare_access_log_chart()
                widget.data = {
                    "by_day": self.data["accessLogByDay"]
                }
            elif widget.widget == "audit_log_latest":
                self.prepare_audit_log_latest()
                widget.data = {
                    "log_entries": self.data["latestAuditLog"][:10]
                }
            elif widget.widget == "pending_registration_requests":
                self.prepare_pending_registration_requests()
                widget.data = {
                    "requests": self.data["pendingRegistrationRequests"][:10]
                }
            elif widget.widget == "space_status":
                self.prepare_space_status()
                state = self.data["spaceState"]
                is_stale = (
                    state is not None
                    and timezone.now() - state.updated > timedelta(hours=12)
                )
                widget.data = {
                    "state": state,
                    "is_stale": is_stale,
                    "weeks": self.data["spaceHeatmapWeeks"]
                }
            elif widget.widget == "machines_maintenance":
                self.prepare_machines_maintenance()
                widget.data = {
                    "machines": self.data["maintenanceMachines"][:10]
                }
