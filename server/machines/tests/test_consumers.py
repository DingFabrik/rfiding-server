from unittest.mock import AsyncMock, MagicMock, patch

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TransactionTestCase

from machines.consumers import MachineLogConsumer, MachineStateConsumer
from machines.models import Machine

User = get_user_model()


def build_scope(mac_address, user):
    return {
        "type": "websocket",
        "user": user,
        "url_route": {"kwargs": {"mac_address": mac_address}},
    }


async def grant(user, *codenames):
    permissions = [p async for p in Permission.objects.filter(codename__in=codenames)]
    await user.user_permissions.aadd(*permissions)
    return await User.objects.aget(pk=user.pk)


def fake_connection_manager():
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    return manager


class MachineStateConsumerTests(TransactionTestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    async def test_anonymous_user_is_rejected(self):
        communicator = WebsocketCommunicator(
            MachineStateConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/state"
        )
        communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", AnonymousUser()))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_without_permission_is_rejected(self):
        communicator = WebsocketCommunicator(
            MachineStateConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/state"
        )
        communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", self.user))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_with_permission_connects_and_disconnects_cleanly(self):
        self.user = await grant(self.user, "view_machine_state")
        fake_manager = fake_connection_manager()

        with patch("machines.consumers.ConnectionManager", return_value=fake_manager):
            communicator = WebsocketCommunicator(
                MachineStateConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/state"
            )
            communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_nothing(timeout=0.1)
            fake_manager.connect.assert_awaited_once()

            await communicator.disconnect()
            fake_manager.disconnect.assert_awaited_once()

    async def test_command_ignored_without_send_permission(self):
        self.user = await grant(self.user, "view_machine_state")
        fake_manager = fake_connection_manager()

        with patch("machines.consumers.ConnectionManager", return_value=fake_manager):
            communicator = WebsocketCommunicator(
                MachineStateConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/state"
            )
            communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_nothing(timeout=0.1)

            await communicator.send_json_to({"command": "enable"})
            fake_manager.send_command.assert_not_called()

            await communicator.disconnect()

    async def test_command_forwarded_with_send_permission(self):
        self.user = await grant(
            self.user, "view_machine_state", "send_machine_commands"
        )
        fake_manager = fake_connection_manager()

        with patch("machines.consumers.ConnectionManager", return_value=fake_manager):
            communicator = WebsocketCommunicator(
                MachineStateConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/state"
            )
            communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_nothing(timeout=0.1)

            await communicator.send_json_to({"command": "enable"})
            await communicator.receive_nothing(timeout=0.1)
            fake_manager.send_command.assert_called_once_with("enable")

            await communicator.disconnect()

    async def test_state_update_sends_rendered_partial(self):
        self.user = await grant(self.user, "view_machine_state")
        fake_manager = fake_connection_manager()

        with patch("machines.consumers.ConnectionManager", return_value=fake_manager):
            communicator = WebsocketCommunicator(
                MachineStateConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/state"
            )
            communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_nothing(timeout=0.1)

            await fake_manager.on_state_change({"state": "enabled"})
            response = await communicator.receive_from()
            self.assertIn("Enabled", response)

            await communicator.disconnect()


class MachineLogConsumerTests(TransactionTestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    async def test_anonymous_user_is_rejected(self):
        communicator = WebsocketCommunicator(
            MachineLogConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/logs"
        )
        communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", AnonymousUser()))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_with_permission_connects_and_subscribes_to_logs(self):
        self.user = await grant(self.user, "view_machine_state")
        fake_manager = fake_connection_manager()
        fake_manager.client.subscribe_logs = MagicMock()

        with patch("machines.consumers.ConnectionManager", return_value=fake_manager):
            communicator = WebsocketCommunicator(
                MachineLogConsumer.as_asgi(), "/ws/machines/aa:bb:cc:dd:ee:ff/logs"
            )
            communicator.scope.update(build_scope("aa:bb:cc:dd:ee:ff", self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_nothing(timeout=0.1)

            fake_manager.connect.assert_awaited_once()
            fake_manager.client.subscribe_logs.assert_called_once()

            await communicator.disconnect()
