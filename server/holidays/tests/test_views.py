from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from holidays.models import Holiday

User = get_user_model()


class HolidayViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.admin)

    def test_list_view(self):
        response = self.client.get(reverse("holidays:list"))
        self.assertEqual(response.status_code, 200)

    def test_create_page_renders(self):
        response = self.client.get(reverse("holidays:create"))
        self.assertEqual(response.status_code, 200)

    def test_create_holiday(self):
        response = self.client.post(
            reverse("holidays:create"),
            {"name": "New Year", "date": "2025-01-01", "repeats_annually": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Holiday.objects.filter(name="New Year").exists())

    def test_update_page_renders(self):
        holiday = Holiday.objects.create(
            name="Old", date="2024-12-25", repeats_annually=True
        )
        response = self.client.get(reverse("holidays:update", kwargs={"pk": holiday.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_delete"])

    def test_update_holiday(self):
        holiday = Holiday.objects.create(
            name="Old", date="2024-12-25", repeats_annually=True
        )
        response = self.client.post(
            reverse("holidays:update", kwargs={"pk": holiday.pk}),
            {"name": "New", "date": "2024-12-25", "repeats_annually": "on"},
        )
        self.assertEqual(response.status_code, 302)
        holiday.refresh_from_db()
        self.assertEqual(holiday.name, "New")

    def test_delete_holiday(self):
        holiday = Holiday.objects.create(name="Old", date="2024-12-25")
        response = self.client.post(reverse("holidays:delete", kwargs={"pk": holiday.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Holiday.objects.filter(pk=holiday.pk).exists())
