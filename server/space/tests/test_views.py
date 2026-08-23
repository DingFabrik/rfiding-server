from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from space.models import SpaceState


class ShowSpaceStatusTests(TestCase):
    url = reverse("space:status")

    def test_no_state_configured(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["state"])
        self.assertNotIn("state_text", response.context)
        self.assertNotIn("warning", response.context)

    def test_open_state_recently_updated(self):
        SpaceState.objects.create(is_open=True)
        response = self.client.get(self.url)
        self.assertEqual(response.context["state_text"], "open")
        self.assertNotIn("warning", response.context)

    def test_closed_state_recently_updated(self):
        SpaceState.objects.create(is_open=False)
        response = self.client.get(self.url)
        self.assertEqual(response.context["state_text"], "closed")
        self.assertNotIn("warning", response.context)

    def test_stale_state_shows_warning(self):
        state = SpaceState.objects.create(is_open=True)
        stale_time = timezone.now() - timedelta(hours=13)
        SpaceState.objects.filter(pk=state.pk).update(updated=stale_time)

        response = self.client.get(self.url)
        self.assertIn("warning", response.context)

    def test_space_name_in_context(self):
        response = self.client.get(self.url)
        self.assertIn("space_name", response.context)
