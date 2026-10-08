from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from access_log.models import (
    AccessLog,
    LOG_TYPE_DISABLED,
    LOG_TYPE_ENABLED,
    LOG_TYPE_UNSUCCESSFUL,
)
from access_log.statistics import compute_global_statistics, parse_days
from machines.models import Machine
from people.models import Person, Qualification
from space.models import SpaceState
from tokens.models import Token


def create_log(machine, type, token=None, ago=timedelta(0), duration=None):
    log = AccessLog.objects.create(
        machine=machine, token=token, type=type, enabled_duration=duration
    )
    AccessLog.objects.filter(pk=log.pk).update(timestamp=timezone.now() - ago)
    return log


class ParseDaysTests(TestCase):
    def test_accepts_known_choices(self):
        self.assertEqual(parse_days("7"), 7)
        self.assertEqual(parse_days(365), 365)

    def test_falls_back_to_default(self):
        self.assertEqual(parse_days(None), 90)
        self.assertEqual(parse_days("abc"), 90)
        self.assertEqual(parse_days("12"), 90)


class GlobalStatisticsTests(TestCase):
    def setUp(self):
        self.lathe = Machine.objects.create(mac_address="aa:aa:aa:aa:aa:aa", hostname="lathe", name="Lathe")
        self.laser = Machine.objects.create(mac_address="bb:bb:bb:bb:bb:bb", hostname="laser", name="Laser")
        self.idle = Machine.objects.create(mac_address="cc:cc:cc:cc:cc:cc", hostname="idle", name="Idle")
        self.alice = Person.objects.create(name="Alice", email="alice@example.com")
        self.bob = Person.objects.create(name="Bob", email="bob@example.com")
        self.alice_token = Token.objects.create(serial="1", person=self.alice)
        self.bob_token = Token.objects.create(serial="2", person=self.bob)

    def test_empty(self):
        stats = compute_global_statistics(30)
        self.assertEqual(stats["total_accesses"], 0)
        self.assertEqual(stats["usage_hours"], 0)
        self.assertIsNone(stats["access_change"])
        self.assertEqual(stats["top_machines"], [])
        self.assertEqual(stats["idle_machine_count"], 3)

    def test_totals_and_rankings(self):
        create_log(self.lathe, LOG_TYPE_ENABLED, self.alice_token)
        create_log(self.lathe, LOG_TYPE_ENABLED, self.alice_token)
        create_log(self.lathe, LOG_TYPE_ENABLED, self.bob_token)
        create_log(self.lathe, LOG_TYPE_DISABLED, self.alice_token, duration=timedelta(hours=2))
        create_log(self.laser, LOG_TYPE_ENABLED, self.alice_token)
        create_log(self.laser, LOG_TYPE_UNSUCCESSFUL, self.bob_token)
        # Outside the timeframe
        create_log(self.idle, LOG_TYPE_ENABLED, self.bob_token, ago=timedelta(days=40))

        stats = compute_global_statistics(30)

        self.assertEqual(stats["total_accesses"], 4)
        self.assertEqual(stats["unsuccessful_attempts"], 1)
        self.assertEqual(stats["active_people"], 2)
        self.assertEqual(stats["active_machines"], 2)
        self.assertEqual(stats["usage_hours"], 2)

        lathe, laser = stats["top_machines"]
        self.assertEqual((lathe["machine__name"], lathe["accesses"], lathe["people"]), ("Lathe", 3, 2))
        self.assertEqual(lathe["usage_hours"], 2)
        self.assertEqual((laser["machine__name"], laser["unsuccessful"]), ("Laser", 1))

        alice, bob = stats["top_people"]
        self.assertEqual((alice["token__person__name"], alice["accesses"], alice["machines"]), ("Alice", 3, 2))
        self.assertEqual((bob["token__person__name"], bob["accesses"]), ("Bob", 1))

        self.assertEqual(list(stats["idle_machines"]), [self.idle])

    def test_access_change_against_previous_period(self):
        create_log(self.lathe, LOG_TYPE_ENABLED, ago=timedelta(days=10))
        create_log(self.lathe, LOG_TYPE_ENABLED, ago=timedelta(days=10))
        create_log(self.lathe, LOG_TYPE_ENABLED, ago=timedelta(days=10))
        create_log(self.lathe, LOG_TYPE_ENABLED, ago=timedelta(days=40))
        create_log(self.lathe, LOG_TYPE_ENABLED, ago=timedelta(days=40))

        stats = compute_global_statistics(30)

        self.assertEqual(stats["access_change"], 50)

    def test_counts_qualifications_in_timeframe(self):
        Qualification.objects.create(person=self.alice, machine=self.lathe)
        old = Qualification.objects.create(person=self.bob, machine=self.lathe)
        Qualification.objects.filter(pk=old.pk).update(
            created=timezone.now() - timedelta(days=60),
            expired=timezone.now() - timedelta(days=1),
        )

        stats = compute_global_statistics(30)

        self.assertEqual(stats["qualifications_granted"], 1)
        self.assertEqual(stats["qualifications_expired"], 1)

    def test_hourly_counts_sum_across_days(self):
        timestamp = timezone.now() - timedelta(days=1)
        for days_ago in (0, 1, 2):
            log = create_log(self.lathe, LOG_TYPE_ENABLED)
            AccessLog.objects.filter(pk=log.pk).update(timestamp=timestamp - timedelta(days=days_ago))

        stats = compute_global_statistics(7)

        hour = timezone.localtime(timestamp).hour
        self.assertEqual(stats["access_by_hour"][hour]["count"], 3)


class QualificationInsightTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(mac_address="aa:aa:aa:aa:aa:aa", hostname="m", name="Lathe")
        self.now = timezone.now()

    def qualify(self, name, created_ago, **fields):
        person = Person.objects.create(name=name, email=f"{name}@example.com")
        qualification = Qualification.objects.create(person=person, machine=self.machine, **fields)
        Qualification.objects.filter(pk=qualification.pk).update(created=self.now - created_ago)
        return qualification

    def test_unused_qualifications(self):
        self.qualify("never", timedelta(days=60))
        self.qualify("stale", timedelta(days=60), last_used=self.now - timedelta(days=40))
        self.qualify("recent", timedelta(days=60), last_used=self.now - timedelta(days=2))
        self.qualify("new", timedelta(days=5))
        self.qualify("expired", timedelta(days=60), expired=self.now - timedelta(days=1))

        unused = compute_global_statistics(30)["unused_qualifications"]

        self.assertEqual(unused["qualified_total"], 3)
        self.assertEqual(unused["unused_total"], 2)
        (row,) = unused["machines"]
        self.assertEqual((row["machine__name"], row["qualified"], row["unused"]), ("Lathe", 3, 2))

    def test_expiring_qualifications(self):
        soon = self.qualify("soon", timedelta(days=60), expires_at=self.now + timedelta(days=3))
        later = self.qualify("later", timedelta(days=60), expires_at=self.now + timedelta(days=20))
        self.qualify("far", timedelta(days=60), expires_at=self.now + timedelta(days=90))
        self.qualify("past", timedelta(days=60), expires_at=self.now - timedelta(days=1))

        stats = compute_global_statistics(30)

        self.assertEqual(stats["expiring_qualification_count"], 2)
        self.assertEqual(list(stats["expiring_qualifications"]), [soon, later])


# Frozen so the statistics see the same "now" as the test; otherwise the
# currently open period grows by however long the test took to run.
@freeze_time("2024-04-16 12:00")
class SpaceUsageTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(mac_address="aa:aa:aa:aa:aa:aa", hostname="m", name="Lathe")
        self.now = timezone.now()

    def set_state(self, is_open, ago):
        state = SpaceState.objects.create(is_open=is_open)
        SpaceState.objects.filter(pk=state.pk).update(created=self.now - ago)

    def test_without_space_states(self):
        self.assertIsNone(compute_global_statistics(7)["space_usage"])

    def test_open_hours_and_accesses_while_closed(self):
        self.set_state(True, timedelta(days=3, hours=10))
        self.set_state(False, timedelta(days=3, hours=6))
        self.set_state(True, timedelta(hours=2))
        create_log(self.machine, LOG_TYPE_ENABLED, ago=timedelta(days=3, hours=8))
        create_log(self.machine, LOG_TYPE_DISABLED, ago=timedelta(days=3, hours=7), duration=timedelta(hours=1))
        create_log(self.machine, LOG_TYPE_ENABLED, ago=timedelta(days=2))
        create_log(self.machine, LOG_TYPE_ENABLED, ago=timedelta(hours=1))

        space = compute_global_statistics(7)["space_usage"]

        self.assertAlmostEqual(space["open_hours"], 6, places=2)
        self.assertEqual(space["accesses_closed"], 1)
        self.assertAlmostEqual(space["closed_percent"], 100 / 3)
        self.assertAlmostEqual(space["machines_running"], 1 / 6)
        self.assertEqual(len(space["by_day"]), 7)
        self.assertAlmostEqual(sum(day["open_hours"] for day in space["by_day"]), 6, places=1)

    def test_space_open_since_before_timeframe(self):
        self.set_state(True, timedelta(days=30))

        space = compute_global_statistics(7)["space_usage"]

        self.assertAlmostEqual(space["open_hours"], 7 * 24, places=2)


class StatisticsViewTests(TestCase):
    def setUp(self):
        self.url = reverse("statistics")

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_user_without_permission_is_rejected(self):
        user = get_user_model().objects.create_user(email="nobody@example.com", password="pass")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_renders_for_superuser(self):
        user = get_user_model().objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(mac_address="aa:aa:aa:aa:aa:aa", hostname="m", name="Lathe")
        person = Person.objects.create(name="Alice", email="alice@example.com")
        create_log(machine, LOG_TYPE_ENABLED, Token.objects.create(serial="1", person=person))
        Qualification.objects.create(
            person=Person.objects.create(name="Bob", email="bob@example.com"),
            machine=machine,
            expires_at=timezone.now() + timedelta(days=3),
        )
        SpaceState.objects.create(is_open=True)

        response = self.client.get(self.url, {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_days"], 7)
        self.assertEqual(len(response.context["access_by_day"]), 7)
        self.assertContains(response, "Lathe")
        self.assertContains(response, "Alice")
        self.assertContains(response, f'href="{self.url}"')
        self.assertContains(response, "Bob")
        self.assertContains(response, 'id="space-usage-by-day"')

    def test_invalid_days_falls_back_to_default(self):
        user = get_user_model().objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        response = self.client.get(self.url, {"days": "nope"})
        self.assertEqual(response.context["selected_days"], 90)


class GenerateDemoStatisticsCommandTests(TestCase):
    def test_generates_and_clears_demo_data(self):
        existing = Machine.objects.create(mac_address="aa:aa:aa:aa:aa:aa", hostname="real", name="Real")

        call_command("generate_demo_statistics", people=10, days=30, stdout=StringIO())

        self.assertTrue(Machine.objects.filter(hostname__startswith="demo-").exists())
        self.assertEqual(Person.objects.count(), 10)
        self.assertTrue(AccessLog.objects.filter(type=LOG_TYPE_ENABLED).exists())
        self.assertFalse(AccessLog.objects.filter(timestamp__gt=timezone.now()).exists())
        with self.assertRaises(CommandError):
            call_command("generate_demo_statistics", people=10, days=30, stdout=StringIO())

        call_command("generate_demo_statistics", people=5, days=7, clear=True, stdout=StringIO())

        self.assertEqual(Person.objects.count(), 5)
        self.assertTrue(Machine.objects.filter(pk=existing.pk).exists())
        self.assertTrue(SpaceState.objects.exists())
        self.assertTrue(Qualification.objects.filter(expires_at__isnull=False).exists())

    def test_keeps_real_space_states(self):
        SpaceState.objects.create(is_open=True)

        call_command("generate_demo_statistics", people=5, days=7, stdout=StringIO())
        call_command("generate_demo_statistics", people=5, days=7, clear=True, stdout=StringIO())

        self.assertEqual(SpaceState.objects.count(), 1)
