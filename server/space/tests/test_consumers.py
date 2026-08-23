import json

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from space.consumers import SpaceStateConsumer
from space.models import SpaceState


@override_settings(SPACE_STATE_SECRET="test-secret")
class SpaceStateConsumerTests(TransactionTestCase):
    async def connect(self):
        communicator = WebsocketCommunicator(
            SpaceStateConsumer.as_asgi(), "/ws/space/status/"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_connect_sends_current_state_closed_by_default(self):
        communicator = await self.connect()
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"state": False})
        await communicator.disconnect()

    async def test_connect_sends_current_open_state(self):
        await SpaceState.objects.acreate(is_open=True)
        communicator = await self.connect()
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"state": True})
        await communicator.disconnect()

    async def test_ping_pong_and_empty_messages_are_ignored(self):
        communicator = await self.connect()
        await communicator.receive_from()  # initial state message

        for text in ("ping", "PONG"):
            await communicator.send_to(text_data=text)
            await communicator.receive_nothing(timeout=0.1)

        await communicator.send_input({"type": "websocket.receive", "text": ""})
        await communicator.receive_nothing(timeout=0.1)

        await communicator.disconnect()

    async def test_invalid_method_returns_error(self):
        communicator = await self.connect()
        await communicator.receive_from()  # initial state message

        await communicator.send_to(text_data=json.dumps({"method": "bogus"}))
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"error": "invalid method"})

        await communicator.disconnect()

    async def test_change_state_with_wrong_secret_is_rejected_and_closes(self):
        communicator = await self.connect()
        await communicator.receive_from()  # initial state message

        await communicator.send_to(
            text_data=json.dumps(
                {"method": "change_state", "secret": "wrong", "state": "1"}
            )
        )
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"error": "invalid secret"})

        closed = await communicator.receive_output(timeout=1)
        self.assertEqual(closed["type"], "websocket.close")

        self.assertFalse(await SpaceState.objects.aexists())

    async def test_change_state_with_non_string_secret_is_rejected(self):
        communicator = await self.connect()
        await communicator.receive_from()  # initial state message

        await communicator.send_to(
            text_data=json.dumps(
                {"method": "change_state", "secret": 12345, "state": "1"}
            )
        )
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"error": "invalid secret"})

    async def test_change_state_with_correct_secret_updates_and_broadcasts(self):
        communicator = await self.connect()
        await communicator.receive_from()  # initial state message

        await communicator.send_to(
            text_data=json.dumps(
                {"method": "change_state", "secret": "test-secret", "state": "1"}
            )
        )
        response = json.loads(await communicator.receive_from())
        self.assertEqual(response, {"state": True})

        state = await SpaceState.objects.afirst()
        self.assertTrue(state.is_open)

        await communicator.disconnect()
