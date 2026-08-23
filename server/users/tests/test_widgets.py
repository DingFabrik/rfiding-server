from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from access_log.models import AccessLog, LOG_TYPE_DISABLED, LOG_TYPE_ENABLED
from machines.models import Machine, MachineRegistrationRequest
from people.models import Person
from space.models import SpaceState
from tokens.models import Token
from users.models import UserWidget
from users.widgets import SPACE_HEATMAP_WEEKS, WidgetDataProvider

User = get_user_model()


class TokenCountsTests(TestCase):
    def test_counts_active_and_total(self):
        person = Person.objects.create(name="p", email="p@example.com")
        Token.objects.create(serial="1", person=person, purpose="a", is_active=True)
        Token.objects.create(serial="2", person=person, purpose="b", is_active=False)

        provider = WidgetDataProvider()
        provider.prepare_token_counts()
        self.assertEqual(provider.data["tokenCount"], 2)
        self.assertEqual(provider.data["activeTokenCount"], 1)

    def test_memoizes_across_calls(self):
        provider = WidgetDataProvider()
        provider.prepare_token_counts()
        person = Person.objects.create(name="p", email="p@example.com")
        Token.objects.create(serial="1", person=person, purpose="a")
        provider.prepare_token_counts()
        self.assertEqual(provider.data["tokenCount"], 0)


class MachineCountsTests(TestCase):
    def test_counts_by_state(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="m1",
            state=Machine.MachineStatus.ACTIVE,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="m2", name="m2",
            state=Machine.MachineStatus.MAINTENANCE,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:03", hostname="m3", name="m3",
            state=Machine.MachineStatus.INACTIVE,
        )

        provider = WidgetDataProvider()
        provider.prepare_machine_counts()
        self.assertEqual(provider.data["machineCount"], 3)
        self.assertEqual(provider.data["activeMachineCount"], 1)
        self.assertEqual(provider.data["maintenanceMachineCount"], 1)


class PersonCountsTests(TestCase):
    def test_counts_active_and_total(self):
        Person.objects.create(name="a", email="a@example.com", is_active=True)
        Person.objects.create(name="b", email="b@example.com", is_active=False)

        provider = WidgetDataProvider()
        provider.prepare_person_counts()
        self.assertEqual(provider.data["peopleCount"], 2)
        self.assertEqual(provider.data["activePeopleCount"], 1)


class AccessLogLatestTests(TestCase):
    def test_selects_related_machine_and_token(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        person = Person.objects.create(name="p", email="p@example.com")
        token = Token.objects.create(serial="1", person=person, purpose="a")
        AccessLog.objects.create(machine=machine, token=token, type=LOG_TYPE_ENABLED)

        provider = WidgetDataProvider()
        provider.prepare_access_log_latest()
        self.assertEqual(provider.data["latestAccessLog"].count(), 1)


class AccessLogChartTests(TestCase):
    def test_counts_enabled_events_per_day(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        AccessLog.objects.create(machine=machine, type=LOG_TYPE_ENABLED)
        AccessLog.objects.create(machine=machine, type=LOG_TYPE_ENABLED)
        AccessLog.objects.create(machine=machine, type=LOG_TYPE_DISABLED)

        provider = WidgetDataProvider()
        provider.prepare_access_log_chart()
        by_day = provider.data["accessLogByDay"]
        self.assertEqual(len(by_day), 14)
        today_label = timezone.localdate().strftime("%d.%m")
        today_entry = next(d for d in by_day if d["day"] == today_label)
        self.assertEqual(today_entry["count"], 2)


class AuditLogLatestTests(TestCase):
    def test_includes_auto_logged_changes(self):
        Person.objects.create(name="p", email="p@example.com")

        provider = WidgetDataProvider()
        provider.prepare_audit_log_latest()
        self.assertGreaterEqual(provider.data["latestAuditLog"].count(), 1)


class PendingRegistrationRequestsTests(TestCase):
    def test_lists_requests_newest_first(self):
        MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="old", ip_address="1.1.1.1"
        )
        MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="new", ip_address="1.1.1.2"
        )

        provider = WidgetDataProvider()
        provider.prepare_pending_registration_requests()
        requests = list(provider.data["pendingRegistrationRequests"])
        self.assertEqual(requests[0].hostname, "new")


class MachinesMaintenanceTests(TestCase):
    def test_lists_only_maintenance_machines(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="m1",
            state=Machine.MachineStatus.MAINTENANCE,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="m2", name="m2",
            state=Machine.MachineStatus.ACTIVE,
        )

        provider = WidgetDataProvider()
        provider.prepare_machines_maintenance()
        self.assertEqual(provider.data["maintenanceMachines"].count(), 1)


class SpaceStatusTests(TestCase):
    def test_no_state_gives_empty_heatmap(self):
        provider = WidgetDataProvider()
        provider.prepare_space_status()
        self.assertIsNone(provider.data["spaceState"])
        weeks = provider.data["spaceHeatmapWeeks"]
        self.assertEqual(len(weeks), SPACE_HEATMAP_WEEKS)
        for week in weeks:
            self.assertEqual(len(week), 7)

    def test_currently_open_state_gives_nonzero_hours_today(self):
        SpaceState.objects.create(is_open=True)
        provider = WidgetDataProvider()
        provider.prepare_space_status()
        weeks = provider.data["spaceHeatmapWeeks"]
        today = timezone.localdate()
        today_cell = next(
            day for week in weeks for day in week if day is not None and day["date"] == today
        )
        self.assertGreater(today_cell["hours"], 0)
        self.assertGreaterEqual(today_cell["level"], 1)


class ProvideForWidgetsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    def make_widget(self, widget_type):
        return UserWidget.objects.create(user=self.user, widget=widget_type)

    def test_token_counts_widget_data(self):
        widget = self.make_widget("token_counts")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(widget.data, {"active_count": 0, "total_count": 0})

    def test_machine_counts_widget_data(self):
        widget = self.make_widget("machine_counts")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(
            widget.data,
            {"active_count": 0, "maintenance_count": 0, "total_count": 0},
        )

    def test_people_counts_widget_data(self):
        widget = self.make_widget("people_counts")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(widget.data, {"active_count": 0, "total_count": 0})

    def test_access_log_latest_widget_data_limits_to_ten(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        for _ in range(12):
            AccessLog.objects.create(machine=machine, type=LOG_TYPE_ENABLED)
        widget = self.make_widget("access_log_latest")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(len(widget.data["log_entries"]), 10)

    def test_access_log_chart_widget_data(self):
        widget = self.make_widget("access_log_chart")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(len(widget.data["by_day"]), 14)

    def test_audit_log_latest_widget_data(self):
        Person.objects.create(name="p", email="p@example.com")
        widget = self.make_widget("audit_log_latest")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertIn("log_entries", widget.data)

    def test_pending_registration_requests_widget_data(self):
        MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="h", ip_address="1.1.1.1"
        )
        widget = self.make_widget("pending_registration_requests")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(len(widget.data["requests"]), 1)

    def test_space_status_widget_data_marks_stale(self):
        state = SpaceState.objects.create(is_open=True)
        SpaceState.objects.filter(pk=state.pk).update(
            updated=timezone.now() - timedelta(hours=13)
        )
        widget = self.make_widget("space_status")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertTrue(widget.data["is_stale"])

    def test_space_status_widget_data_not_stale_when_recent(self):
        SpaceState.objects.create(is_open=True)
        widget = self.make_widget("space_status")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertFalse(widget.data["is_stale"])

    def test_machines_maintenance_widget_data(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="m1",
            state=Machine.MachineStatus.MAINTENANCE,
        )
        widget = self.make_widget("machines_maintenance")
        WidgetDataProvider().provide_for_widgets([widget])
        self.assertEqual(len(widget.data["machines"]), 1)

    def test_shared_provider_reuses_cached_data_across_widgets(self):
        person = Person.objects.create(name="p", email="p@example.com")
        Token.objects.create(serial="1", person=person, purpose="a")
        provider = WidgetDataProvider()
        w1 = self.make_widget("token_counts")
        provider.provide_for_widgets([w1])
        Token.objects.create(serial="2", person=person, purpose="b")
        w2 = self.make_widget("token_counts")
        provider.provide_for_widgets([w2])
        self.assertEqual(w1.data["total_count"], w2.data["total_count"])
