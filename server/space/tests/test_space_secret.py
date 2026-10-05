import json

from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from space.checks import check_space_state_secret, check_space_state_secret_strength
from space.consumers import SpaceStateConsumer
from space.models import SpaceState


class EmptySecretTests(APITestCase):
    url = reverse("api:v1:space_status")

    @override_settings(SPACE_STATE_SECRET="")
    def test_empty_secret_never_matches(self):
        response = self.client.get(self.url, {"secret": "", "state": "open"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SpaceState.objects.exists())

    @override_settings(SPACE_STATE_SECRET="")
    def test_empty_secret_never_matches_on_post(self):
        response = self.client.post(self.url, {"secret": "", "state": "open"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SpaceState.objects.exists())

    @override_settings(SPACE_STATE_SECRET=None)
    def test_unset_secret_never_matches(self):
        response = self.client.get(self.url, {"secret": "", "state": "open"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(SPACE_STATE_SECRET="test-secret")
class SecretTransportTests(APITestCase):
    url = reverse("api:v1:space_status")

    def test_post_with_secret_header(self):
        response = self.client.post(
            self.url, {"state": "open"}, HTTP_X_SPACE_SECRET="test-secret"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(SpaceState.objects.first().is_open)

    def test_post_with_secret_in_body(self):
        response = self.client.post(self.url, {"secret": "test-secret", "state": "open"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(SpaceState.objects.first().is_open)

    def test_post_with_wrong_secret(self):
        response = self.client.post(
            self.url, {"state": "open"}, HTTP_X_SPACE_SECRET="wrong"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SpaceState.objects.exists())

    def test_post_without_secret(self):
        response = self.client.post(self.url, {"state": "open"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_ascii_secret_is_rejected_not_500(self):
        response = self.client.post(self.url, {"secret": "geheim-ü", "state": "open"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SpaceSecretCheckTests(TestCase):
    @override_settings(SPACE_STATE_SECRET="")
    def test_empty_secret_is_an_error(self):
        self.assertEqual([e.id for e in check_space_state_secret(None)], ["space.E001"])

    @override_settings(SPACE_STATE_SECRET="12345")
    def test_short_secret_is_a_deploy_warning(self):
        self.assertEqual(check_space_state_secret(None), [])
        self.assertEqual(
            [e.id for e in check_space_state_secret_strength(None)], ["space.W001"]
        )

    @override_settings(SPACE_STATE_SECRET="a-long-and-random-enough-secret")
    def test_long_secret_passes(self):
        self.assertEqual(check_space_state_secret(None), [])
        self.assertEqual(check_space_state_secret_strength(None), [])


class SpaceSecretConsumerTests(TransactionTestCase):
    async def connect(self):
        communicator = WebsocketCommunicator(
            SpaceStateConsumer.as_asgi(), "/ws/space/status/"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_from()  # initial state message
        return communicator

    @override_settings(SPACE_STATE_SECRET="")
    async def test_empty_secret_is_rejected(self):
        communicator = await self.connect()
        await communicator.send_to(
            text_data=json.dumps({"method": "change_state", "secret": "", "state": "open"})
        )
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"error": "invalid secret"})
        self.assertFalse(await SpaceState.objects.aexists())
        await communicator.disconnect()

    @override_settings(SPACE_STATE_SECRET="test-secret")
    async def test_malformed_messages_do_not_crash(self):
        communicator = await self.connect()
        for text in ("{not json", json.dumps([1, 2]), json.dumps({"secret": "x"})):
            await communicator.send_to(text_data=text)
            response = json.loads(await communicator.receive_from())
            self.assertIn("error", response)
        await communicator.send_to(
            text_data=json.dumps({"method": "change_state", "secret": "test-secret"})
        )
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"error": "missing state"})
        await communicator.disconnect()
