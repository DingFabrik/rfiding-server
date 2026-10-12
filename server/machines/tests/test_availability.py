import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from machines.availability import get_availability, get_usage_rows
from machines.models import Machine, MachineTime

# A Wednesday.
WEDNESDAY_NOON = timezone.make_aware(datetime.datetime(2026, 10, 14, 12, 0))


class AvailabilityTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(name="Prusa")

    def add_time(self, weekdays, start, end):
        MachineTime.objects.create(
            machine=self.machine,
            weekdays=weekdays,
            start_time=datetime.time(*start),
            end_time=datetime.time(*end),
        )

    def availability(self, now=WEDNESDAY_NOON):
        with patch("machines.availability.is_today_holiday", return_value=False):
            return get_availability(self.machine, now)

    def test_no_times_is_usable(self):
        self.assertEqual(self.availability().status, "usable")

    def test_usable_until_end_of_window(self):
        self.add_time([0, 1, 2, 3, 4], (9, 0), (22, 0))
        availability = self.availability()
        self.assertEqual(availability.status, "usable")
        self.assertIn("22:00", availability.headline)

    def test_closed_shows_next_opening(self):
        self.add_time([5, 6], (11, 0), (18, 0))
        availability = self.availability()
        self.assertEqual(availability.status, "closed")
        self.assertIn("Sat", availability.detail)

    def test_maintenance(self):
        self.machine.state = Machine.MachineStatus.MAINTENANCE
        self.machine.maintenance_message = "Nozzle clogged"
        availability = self.availability()
        self.assertEqual(availability.status, "maintenance")
        self.assertEqual(availability.message, "Nozzle clogged")

    def test_holiday(self):
        self.machine.allowed_on_holidays = False
        with patch("machines.availability.is_today_holiday", return_value=True):
            self.assertEqual(get_availability(self.machine, WEDNESDAY_NOON).status, "closed")

    def test_usage_rows_group_days_and_split_today(self):
        self.add_time([0, 1, 2, 3, 4], (9, 0), (22, 0))
        self.add_time([5, 6], (11, 0), (18, 0))
        rows = get_usage_rows(self.machine, WEDNESDAY_NOON)
        self.assertEqual(
            [(row.label, row.is_today) for row in rows],
            [
                ("Mon – Tue", False),
                ("Wed · today", True),
                ("Thu – Fri", False),
                ("Sat – Sun", False),
            ],
        )

    def test_public_page_renders(self):
        self.add_time([0, 1, 2, 3, 4], (9, 0), (22, 0))
        response = self.client.get(reverse("machines:detail", args=[self.machine.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "machine_public_detail.html")
        self.assertContains(response, "Usage times")
