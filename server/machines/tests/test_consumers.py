from unittest.mock import AsyncMock, patch

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TransactionTestCase

from machines.consumers import MachineLogConsumer, MachineStateConsumer
from machines.esphome import bridge, protocol
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


def communicator_for(consumer, user, mac_address="aa:bb:cc:dd:ee:ff", path="state"):
    communicator = WebsocketCommunicator(
        consumer.as_asgi(), f"/ws/machines/{mac_address}/{path}"
    )
    communicator.scope.update(build_scope(mac_address, user))
    return communicator


class MachineStateConsumerTests(TransactionTestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    async def test_anonymous_user_is_rejected(self):
        communicator = communicator_for(MachineStateConsumer, AnonymousUser())
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_without_permission_is_rejected(self):
        communicator = communicator_for(MachineStateConsumer, self.user)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_unknown_machine_is_rejected(self):
        self.user = await grant(self.user, "view_machine_state")
        communicator = communicator_for(
            MachineStateConsumer, self.user, mac_address="11:22:33:44:55:66"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_sends_current_status_on_connect(self):
        self.user = await grant(self.user, "view_machine_state")
        communicator = communicator_for(MachineStateConsumer, self.user)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        # The machine manager is not running in tests.
        self.assertIn("Offline", await communicator.receive_from())
        await communicator.disconnect()

    async def test_state_pushed_by_manager_is_rendered(self):
        self.user = await grant(self.user, "view_machine_state")
        communicator = communicator_for(MachineStateConsumer, self.user)
        await communicator.connect()
        await communicator.receive_from()

        await get_channel_layer().group_send(
            protocol.machine_group(self.machine.pk),
            {
                "type": "machine.state",
                "status": {"connected": True, "verified": True, "state": "enabled"},
            },
        )
        response = await communicator.receive_from()
        self.assertIn("Enabled", response)
        self.assertNotIn("Unverified", response)
        await communicator.disconnect()

    async def test_unverified_server_is_shown(self):
        self.user = await grant(self.user, "view_machine_state")
        communicator = communicator_for(MachineStateConsumer, self.user)
        await communicator.connect()
        await communicator.receive_from()

        await get_channel_layer().group_send(
            protocol.machine_group(self.machine.pk),
            {
                "type": "machine.state",
                "status": {"connected": True, "verified": False, "state": "standby"},
            },
        )
        self.assertIn("Unverified", await communicator.receive_from())
        await communicator.disconnect()

    async def test_no_badge_when_verification_is_off(self):
        self.user = await grant(self.user, "view_machine_state")
        communicator = communicator_for(MachineStateConsumer, self.user)
        await communicator.connect()
        await communicator.receive_from()

        await get_channel_layer().group_send(
            protocol.machine_group(self.machine.pk),
            {
                "type": "machine.state",
                "status": {"connected": True, "verified": None, "state": "standby"},
            },
        )
        self.assertNotIn("Unverified", await communicator.receive_from())
        await communicator.disconnect()

    async def test_command_ignored_without_send_permission(self):
        self.user = await grant(self.user, "view_machine_state")
        with patch(
            "machines.consumers.bridge.asend_command", new_callable=AsyncMock
        ) as send:
            communicator = communicator_for(MachineStateConsumer, self.user)
            await communicator.connect()
            await communicator.receive_from()
            await communicator.send_json_to({"command": "enable"})
            await communicator.receive_nothing(timeout=0.1)
            send.assert_not_awaited()
            await communicator.disconnect()

    async def test_command_forwarded_with_send_permission(self):
        self.user = await grant(
            self.user, "view_machine_state", "send_machine_commands"
        )
        with patch(
            "machines.consumers.bridge.asend_command", new_callable=AsyncMock
        ) as send:
            communicator = communicator_for(MachineStateConsumer, self.user)
            await communicator.connect()
            await communicator.receive_from()
            await communicator.send_json_to({"command": "enable"})
            await communicator.receive_nothing(timeout=0.1)
            send.assert_awaited_once_with(self.machine.pk, "enable")
            await communicator.disconnect()

    async def test_failed_command_is_reported(self):
        self.user = await grant(
            self.user, "view_machine_state", "send_machine_commands"
        )
        with patch(
            "machines.consumers.bridge.asend_command",
            new_callable=AsyncMock,
            side_effect=bridge.CommandFailed("Machine is offline"),
        ):
            communicator = communicator_for(MachineStateConsumer, self.user)
            await communicator.connect()
            await communicator.receive_from()
            await communicator.send_json_to({"command": "enable"})
            self.assertIn("Machine is offline", await communicator.receive_from())
            await communicator.disconnect()


class MachineLogConsumerTests(TransactionTestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    async def test_anonymous_user_is_rejected(self):
        communicator = communicator_for(MachineLogConsumer, AnonymousUser(), path="logs")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_subscribes_streams_and_unsubscribes(self):
        self.user = await grant(self.user, "view_machine_state")
        with (
            patch(
                "machines.consumers.bridge.asubscribe_logs", new_callable=AsyncMock
            ) as subscribe,
            patch(
                "machines.consumers.bridge.aunsubscribe_logs", new_callable=AsyncMock
            ) as unsubscribe,
        ):
            communicator = communicator_for(MachineLogConsumer, self.user, path="logs")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_nothing(timeout=0.1)
            subscribe.assert_awaited_once()
            self.assertEqual(subscribe.await_args.args[0], self.machine.pk)
            channel_name = subscribe.await_args.args[1]

            await get_channel_layer().send(
                channel_name,
                {"type": "machine.log", "level": 1, "message": "Something broke"},
            )
            response = await communicator.receive_from()
            self.assertIn("Something broke", response)
            self.assertIn("text-error", response)

            await communicator.disconnect()
            unsubscribe.assert_awaited_once_with(self.machine.pk, channel_name)
