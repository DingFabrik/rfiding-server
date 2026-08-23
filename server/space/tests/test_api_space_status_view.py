from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import SpaceState


@override_settings(SPACE_STATE_SECRET="test-secret")
class APISpaceStatusViewTests(APITestCase):
    url = reverse("api:v1:space_status")

    def test_wrong_secret_is_rejected(self):
        response = self.client.get(self.url, {"secret": "wrong", "state": "1"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SpaceState.objects.exists())

    def test_missing_state_is_bad_request(self):
        response = self.client.get(self.url, {"secret": "test-secret"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SpaceState.objects.exists())

    def test_valid_secret_persists_state(self):
        response = self.client.get(self.url, {"secret": "test-secret", "state": "open"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["open"])
        state = SpaceState.objects.first()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_open)

    def test_valid_secret_closes_state(self):
        SpaceState.objects.create(is_open=True)
        response = self.client.get(self.url, {"secret": "test-secret", "state": "0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["open"])
        self.assertFalse(SpaceState.objects.first().is_open)

    def test_read_does_not_mutate_state(self):
        SpaceState.objects.create(is_open=True)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["open"])
        self.assertEqual(SpaceState.objects.count(), 1)

    def test_read_with_no_state_defaults_closed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["open"])
        self.assertFalse(SpaceState.objects.exists())

    def test_setting_same_state_is_a_noop(self):
        SpaceState.objects.create(is_open=True)
        response = self.client.get(self.url, {"secret": "test-secret", "state": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SpaceState.objects.count(), 1)
