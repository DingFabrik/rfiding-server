import json

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TransactionTestCase

from machines.models import Machine
from tokens.consumers import UnknownTokenConsumer
from tokens.models import UnknownToken

User = get_user_model()


def build_scope(user):
    return {"type": "websocket", "user": user}


async def grant(user, *codenames):
    permissions = [p async for p in Permission.objects.filter(codename__in=codenames)]
    await user.user_permissions.aadd(*permissions)
    return await User.objects.aget(pk=user.pk)


class UnknownTokenConsumerTests(TransactionTestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    async def test_anonymous_user_is_rejected(self):
        communicator = WebsocketCommunicator(
            UnknownTokenConsumer.as_asgi(), "/ws/tokens/unknown/"
        )
        communicator.scope.update(build_scope(AnonymousUser()))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_without_view_permission_is_rejected(self):
        communicator = WebsocketCommunicator(
            UnknownTokenConsumer.as_asgi(), "/ws/tokens/unknown/"
        )
        communicator.scope.update(build_scope(self.user))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_with_view_permission_connects(self):
        self.user = await grant(self.user, "view_unknowntoken")
        communicator = WebsocketCommunicator(
            UnknownTokenConsumer.as_asgi(), "/ws/tokens/unknown/"
        )
        communicator.scope.update(build_scope(self.user))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_clear_without_delete_permission_does_not_clear(self):
        await UnknownToken.objects.acreate(serial="123", machine=self.machine)
        self.user = await grant(self.user, "view_unknowntoken")

        communicator = WebsocketCommunicator(
            UnknownTokenConsumer.as_asgi(), "/ws/tokens/unknown/"
        )
        communicator.scope.update(build_scope(self.user))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data=json.dumps({"action": "clear"}))
        await communicator.receive_nothing(timeout=0.1)

        self.assertTrue(await UnknownToken.objects.aexists())
        await communicator.disconnect()

    async def test_clear_with_delete_permission_clears_and_broadcasts(self):
        await UnknownToken.objects.acreate(serial="123", machine=self.machine)
        self.user = await grant(
            self.user, "view_unknowntoken", "delete_unknowntoken"
        )

        communicator = WebsocketCommunicator(
            UnknownTokenConsumer.as_asgi(), "/ws/tokens/unknown/"
        )
        communicator.scope.update(build_scope(self.user))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data=json.dumps({"action": "clear"}))

        response = await communicator.receive_from()
        self.assertIn("no tokens found", response.lower())
        self.assertFalse(await UnknownToken.objects.aexists())

        await communicator.disconnect()

    async def test_unknown_token_list_changed_renders_table_when_tokens_exist(self):
        await UnknownToken.objects.acreate(serial="999", machine=self.machine)
        self.user = await grant(self.user, "view_unknowntoken")

        communicator = WebsocketCommunicator(
            UnknownTokenConsumer.as_asgi(), "/ws/tokens/unknown/"
        )
        communicator.scope.update(build_scope(self.user))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Directly exercise the group-event handler, as if another client's
        # "clear" action (or a new unknown token) had broadcast this event.
        await communicator.send_input({"type": "unknown_token_list_changed"})
        response = await communicator.receive_from()
        self.assertIn("999", response)

        await communicator.disconnect()
