import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aioesphomeapi import (
    ExecuteServiceResponse,
    HomeassistantServiceCall,
    SupportsResponseType,
    UserService,
    UserServiceArg,
    UserServiceArgType,
)
from channels.layers import InMemoryChannelLayer
from django.test import SimpleTestCase, TestCase, override_settings

from access_log.models import LOG_TYPE_UNSUCCESSFUL, AccessLog
from base.build import running_version
from machines.esphome import bridge, protocol
from machines.esphome.connection import CommandError, DeviceConnection, MachineSettings
from machines.esphome.handlers import RequestError, handle_request
from machines.esphome.manager import DeviceManager, load_machine_settings
from machines.models import Machine
from people.models import Person
from tokens.models import Token


def make_settings(pk=1, **kwargs):
    values = {
        "pk": pk,
        "name": f"machine {pk}",
        "address": "10.0.0.1",
        "encryption_key": "key",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "api_key": "api-key",
        "config": {"minPower": 10},
    }
    values.update(kwargs)
    return MachineSettings(**values)


class SignChallengeTests(SimpleTestCase):
    def test_signature_is_hmac_sha256_over_context_and_challenge(self):
        # Fixed vector, the device must compute the same value.
        self.assertEqual(
            protocol.sign_challenge("secret", "0123456789abcdef"),
            "edb17743faceece62694a2c3b77480e908df9041bb0c05594084dcaa6b0e73da",
        )

    def test_signature_depends_on_key_and_challenge(self):
        signature = protocol.sign_challenge("secret", "abc")
        self.assertNotEqual(signature, protocol.sign_challenge("other", "abc"))
        self.assertNotEqual(signature, protocol.sign_challenge("secret", "abd"))


class HandleRequestTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            needs_qualification=False,
            min_power=42,
        )
        person = Person.objects.create(name="test", email="test@example.com")
        Token.objects.create(serial="abc123", person=person)

    def test_check_access_granted(self):
        result = handle_request(
            self.machine.pk, protocol.REQUEST_CHECK_ACCESS, {"token": "ABC123"}
        )
        self.assertIs(result["access"], True)
        self.assertIn("workingtime", result)

    def test_check_access_denied_is_logged(self):
        result = handle_request(
            self.machine.pk, protocol.REQUEST_CHECK_ACCESS, {"token": "unknown"}
        )
        self.assertIs(result["access"], False)
        self.assertEqual(result["error"], "No Access!")
        self.assertTrue(
            AccessLog.objects.filter(
                machine=self.machine, type=LOG_TYPE_UNSUCCESSFUL
            ).exists()
        )

    def test_check_access_needs_token(self):
        with self.assertRaises(RequestError):
            handle_request(self.machine.pk, protocol.REQUEST_CHECK_ACCESS, {})

    def test_config_returns_config_and_stores_reported_info(self):
        result = handle_request(
            self.machine.pk,
            protocol.REQUEST_CONFIG,
            {"firmware_version": "2.0.0", "ip_address": "10.0.0.9"},
        )
        self.assertEqual(result["minPower"], 42)
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.firmware_version, "2.0.0")
        self.assertEqual(self.machine.ip_address, "10.0.0.9")

    def test_disabled_with_unknown_compartment_is_an_error(self):
        with self.assertRaises(RequestError):
            handle_request(
                self.machine.pk, protocol.REQUEST_DISABLED, {"compartment": "9"}
            )

    def test_inactive_machine_is_rejected(self):
        self.machine.state = Machine.MachineStatus.INACTIVE
        self.machine.save()
        with self.assertRaises(RequestError):
            handle_request(
                self.machine.pk, protocol.REQUEST_CHECK_ACCESS, {"token": "abc123"}
            )

    def test_unknown_request_is_rejected(self):
        with self.assertRaises(RequestError):
            handle_request(self.machine.pk, "rfiding.bogus", {})


class LoadMachineSettingsTests(TestCase):
    def test_only_machines_with_key_and_ip_that_are_not_inactive(self):
        managed = Machine.objects.create(
            name="managed", ip_address="10.0.0.1", encryption_key="k", api_key="a"
        )
        Machine.objects.create(name="no key", ip_address="10.0.0.2")
        Machine.objects.create(name="empty key", ip_address="10.0.0.3", encryption_key="")
        Machine.objects.create(name="no ip", encryption_key="k")
        Machine.objects.create(
            name="inactive",
            ip_address="10.0.0.4",
            encryption_key="k",
            state=Machine.MachineStatus.INACTIVE,
        )
        maintenance = Machine.objects.create(
            name="maintenance",
            ip_address="10.0.0.5",
            encryption_key="k",
            state=Machine.MachineStatus.MAINTENANCE,
        )
        settings = load_machine_settings()
        self.assertEqual(set(settings), {managed.pk, maintenance.pk})
        self.assertEqual(settings[managed.pk].api_key, "a")
        self.assertIn("minPower", settings[managed.pk].config)


def fake_service(name, supports_response=SupportsResponseType.STATUS, args=()):
    return UserService(
        name=name,
        key=hash(name) & 0xFFFF,
        args=[UserServiceArg(name=arg, type=UserServiceArgType.STRING) for arg in args],
        supports_response=supports_response,
    )


def entity(key, object_id):
    return SimpleNamespace(key=key, object_id=object_id)


def state(key, value):
    return SimpleNamespace(key=key, state=value, missing_state=False)


ENTITIES = [
    entity(1, protocol.ENTITY_DEVICE_STATE),
    entity(2, protocol.ENTITY_CHALLENGE),
    entity(3, protocol.ENTITY_SERVER_VERIFIED),
    entity(4, protocol.ENTITY_POWER),
]

SERVICES = [
    fake_service(protocol.ACTION_AUTHENTICATE, args=["signature"]),
    fake_service(protocol.ACTION_SET_CONFIG, args=["config"]),
    fake_service(protocol.ACTION_ENABLE, SupportsResponseType.NONE),
    fake_service(protocol.ACTION_RELOAD_CONFIG, SupportsResponseType.NONE),
]


class DeviceConnectionTests(TestCase):
    def setUp(self):
        client_patcher = patch("machines.esphome.connection.APIClient")
        reconnect_patcher = patch("machines.esphome.connection.ReconnectLogic")
        self.client_cls = client_patcher.start()
        reconnect_patcher.start()
        self.addCleanup(client_patcher.stop)
        self.addCleanup(reconnect_patcher.stop)
        self.client = self.client_cls.return_value
        self.client.device_info_and_list_entities = AsyncMock(
            return_value=(SimpleNamespace(project_version="1.2.3"), ENTITIES, SERVICES)
        )
        self.client.execute_service = AsyncMock(
            return_value=ExecuteServiceResponse(success=True)
        )
        self.manager = MagicMock()
        self.manager.publish_status = AsyncMock()
        self.manager.has_log_listeners.return_value = False

    async def connect(self, settings=None):
        connection = DeviceConnection(settings or make_settings(), self.manager)
        await connection._on_connect()
        await self.settle(connection)
        return connection

    async def settle(self, connection):
        while connection._tasks:
            await asyncio.gather(*connection._tasks, return_exceptions=True)

    def executed(self, name):
        return [
            call
            for call in self.client.execute_service.await_args_list
            if call.args[0].name == name
        ]

    async def test_client_identifies_as_rfiding_and_checks_mac(self):
        DeviceConnection(make_settings(), self.manager)
        kwargs = self.client_cls.call_args.kwargs
        self.assertEqual(kwargs["client_info"], protocol.CLIENT_INFO)
        self.assertEqual(kwargs["noise_psk"], "key")
        self.assertEqual(kwargs["expected_mac"], "aabbccddeeff")

    async def test_connect_subscribes_and_pushes_config(self):
        connection = await self.connect()
        self.client.subscribe_states.assert_called_once()
        self.client.subscribe_service_calls.assert_called_once()
        self.assertTrue(connection.connected)
        self.assertEqual(connection.firmware_version, "1.2.3")
        (push,) = self.executed(protocol.ACTION_SET_CONFIG)
        self.assertEqual(json.loads(push.args[1]["config"]), {"minPower": 10})
        self.assertIs(push.kwargs["return_response"], False)

    async def test_challenge_is_answered_with_signature(self):
        connection = await self.connect()
        connection._on_state(state(2, "nonce"))
        await self.settle(connection)
        (auth,) = self.executed(protocol.ACTION_AUTHENTICATE)
        self.assertEqual(
            auth.args[1], {"signature": protocol.sign_challenge("api-key", "nonce")}
        )
        self.assertTrue(connection.verified)
        self.assertTrue(connection.status()["verified"])

    async def test_each_challenge_is_answered_once(self):
        self.client.execute_service.return_value = ExecuteServiceResponse(
            success=False, error_message="Invalid signature"
        )
        connection = await self.connect()
        connection._on_state(state(2, "nonce"))
        await self.settle(connection)
        connection._on_state(state(3, False))
        await self.settle(connection)
        self.assertEqual(len(self.executed(protocol.ACTION_AUTHENTICATE)), 1)
        self.assertFalse(connection.verified)

        connection._on_state(state(2, "new nonce"))
        await self.settle(connection)
        self.assertEqual(len(self.executed(protocol.ACTION_AUTHENTICATE)), 2)

    async def test_no_api_key_means_no_verification(self):
        connection = await self.connect(make_settings(api_key=None))
        connection._on_state(state(2, "nonce"))
        await self.settle(connection)
        self.assertEqual(self.executed(protocol.ACTION_AUTHENTICATE), [])

    async def test_state_changes_are_published(self):
        connection = await self.connect()
        self.manager.publish_status.reset_mock()
        connection._on_state(state(1, "enabled"))
        await self.settle(connection)
        self.manager.publish_status.assert_awaited_once_with(connection)
        self.assertEqual(connection.status()["state"], "enabled")
        # Unchanged values are not published again.
        connection._on_state(state(1, "enabled"))
        await self.settle(connection)
        self.manager.publish_status.assert_awaited_once()

    async def test_device_request_is_answered(self):
        connection = await self.connect()
        call = HomeassistantServiceCall(
            service=protocol.REQUEST_CHECK_ACCESS,
            data={"token": "abc"},
            call_id=7,
            wants_response=True,
        )
        with patch(
            "machines.esphome.connection.handle_request",
            return_value={"access": True},
        ) as handler:
            connection._on_service_call(call)
            await self.settle(connection)
        handler.assert_called_once_with(1, protocol.REQUEST_CHECK_ACCESS, {"token": "abc"})
        self.client.send_homeassistant_action_response.assert_called_once_with(
            7, True, "", b'{"access": true}'
        )

    async def test_failed_device_request_is_answered_with_error(self):
        connection = await self.connect()
        call = HomeassistantServiceCall(service="rfiding.bogus", call_id=8)
        connection._on_service_call(call)
        await self.settle(connection)
        self.client.send_homeassistant_action_response.assert_called_once_with(
            8, False, "Unknown request rfiding.bogus", b""
        )

    async def test_foreign_service_calls_and_events_are_ignored(self):
        connection = await self.connect()
        with patch("machines.esphome.connection.handle_request") as handler:
            connection._on_service_call(
                HomeassistantServiceCall(service="light.turn_on", call_id=1)
            )
            connection._on_service_call(
                HomeassistantServiceCall(
                    service=protocol.REQUEST_CHECK_ACCESS, is_event=True
                )
            )
            await self.settle(connection)
        handler.assert_not_called()

    async def test_commands_need_a_connection(self):
        connection = DeviceConnection(make_settings(), self.manager)
        with self.assertRaisesMessage(CommandError, "offline"):
            await connection.run_command(protocol.ACTION_ENABLE)

    async def test_unsupported_action_is_an_error(self):
        connection = await self.connect()
        with self.assertRaisesMessage(CommandError, "does not support restart"):
            await connection.run_command(protocol.ACTION_RESTART)

    async def test_command_without_response_is_fire_and_forget(self):
        connection = await self.connect()
        await connection.run_command(protocol.ACTION_ENABLE)
        (enable,) = self.executed(protocol.ACTION_ENABLE)
        self.assertIsNone(enable.kwargs["return_response"])

    async def test_reload_config_pushes_config_when_supported(self):
        connection = await self.connect()
        await connection.run_command(protocol.ACTION_RELOAD_CONFIG)
        self.assertEqual(len(self.executed(protocol.ACTION_SET_CONFIG)), 2)
        self.assertEqual(self.executed(protocol.ACTION_RELOAD_CONFIG), [])

    async def test_device_timeout_is_an_error(self):
        connection = await self.connect()
        self.client.execute_service.side_effect = TimeoutError
        with self.assertRaisesMessage(CommandError, "did not answer"):
            await connection.call_action(protocol.ACTION_AUTHENTICATE, {"signature": "x"})

    async def test_disconnect_resets_state(self):
        connection = await self.connect()
        connection._on_state(state(2, "nonce"))
        await self.settle(connection)
        await connection._on_disconnect(False)
        self.assertFalse(connection.connected)
        self.assertFalse(connection.verified)
        self.assertEqual(connection.status()["state"], "disconnected")


class FakeConnection:
    instances = []

    def __init__(self, settings, manager):
        self.settings = settings
        self.manager = manager
        self.connected = False
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.push_config = AsyncMock()
        self.run_command = AsyncMock()
        self.set_log_streaming = MagicMock()
        FakeConnection.instances.append(self)

    @property
    def pk(self):
        return self.settings.pk

    def status(self):
        return {"connected": True, "verified": True, "state": "standby"}


@patch("machines.esphome.manager.DeviceConnection", FakeConnection)
class DeviceManagerTests(TestCase):
    def setUp(self):
        FakeConnection.instances = []
        self.settings = {1: make_settings(1), 2: make_settings(2, address="10.0.0.2")}
        self.layer = InMemoryChannelLayer()
        self.manager = DeviceManager(
            channel_layer=self.layer,
            load_settings=lambda pk=None: {
                key: value
                for key, value in self.settings.items()
                if pk is None or key == pk
            },
        )

    async def settle(self):
        while self.manager._tasks:
            await asyncio.gather(*self.manager._tasks, return_exceptions=True)

    async def test_sync_connects_to_all_managed_machines(self):
        await self.manager.sync()
        self.assertEqual(set(self.manager.connections), {1, 2})
        for connection in FakeConnection.instances:
            connection.start.assert_awaited_once()

    async def test_sync_drops_removed_machines(self):
        await self.manager.sync()
        removed = self.manager.connections[2]
        del self.settings[2]
        await self.manager.sync()
        self.assertEqual(set(self.manager.connections), {1})
        removed.stop.assert_awaited_once()

    async def test_changed_address_reconnects(self):
        await self.manager.sync()
        old = self.manager.connections[1]
        self.settings[1] = make_settings(1, address="10.0.0.99")
        await self.manager.sync(1)
        old.stop.assert_awaited_once()
        self.assertIsNot(self.manager.connections[1], old)
        self.assertEqual(self.manager.connections[1].settings.address, "10.0.0.99")

    async def test_changed_config_is_pushed_without_reconnecting(self):
        await self.manager.sync()
        connection = self.manager.connections[1]
        self.settings[1] = make_settings(1, config={"minPower": 99})
        await self.manager.sync(1)
        await self.settle()
        self.assertIs(self.manager.connections[1], connection)
        connection.stop.assert_not_awaited()
        connection.push_config.assert_awaited_once()

    async def test_changed_api_key_reconnects(self):
        await self.manager.sync()
        old = self.manager.connections[1]
        self.settings[1] = make_settings(1, api_key="new")
        await self.manager.sync(1)
        old.stop.assert_awaited_once()
        self.assertEqual(self.manager.connections[1].settings.api_key, "new")

    async def test_command_is_run_and_acknowledged(self):
        await self.manager.sync()
        reply_channel = await self.layer.new_channel()
        await self.manager.dispatch(
            {
                "type": "machine.command",
                "machine": 1,
                "command": "enable",
                "reply_channel": reply_channel,
            }
        )
        self.manager.connections[1].run_command.assert_awaited_once_with("enable")
        reply = await self.layer.receive(reply_channel)
        self.assertTrue(reply["ok"])

    async def test_command_errors_are_replied(self):
        await self.manager.sync()
        self.manager.connections[1].run_command.side_effect = CommandError("offline")
        reply_channel = await self.layer.new_channel()
        await self.manager.dispatch(
            {
                "type": "machine.command",
                "machine": 1,
                "command": "enable",
                "reply_channel": reply_channel,
            }
        )
        reply = await self.layer.receive(reply_channel)
        self.assertEqual(reply, {"type": "machine.reply", "ok": False, "error": "offline"})

    async def test_unmanaged_machine_is_an_error(self):
        reply_channel = await self.layer.new_channel()
        await self.manager.dispatch(
            {"type": "machine.status", "machine": 5, "reply_channel": reply_channel}
        )
        reply = await self.layer.receive(reply_channel)
        self.assertFalse(reply["ok"])

    async def test_machine_changed_reconnects_offline_machine_immediately(self):
        await self.manager.sync()
        connection = self.manager.connections[1]
        await self.manager.dispatch({"type": "machine.changed", "machine": 1})
        connection.stop.assert_awaited_once()
        self.assertIsNot(self.manager.connections[1], connection)
        self.manager.connections[1].start.assert_awaited_once()

    async def test_machine_changed_keeps_connected_machine(self):
        await self.manager.sync()
        connection = self.manager.connections[1]
        connection.connected = True
        await self.manager.dispatch({"type": "machine.changed", "machine": 1})
        connection.stop.assert_not_awaited()
        self.assertIs(self.manager.connections[1], connection)

    async def test_machine_changed_does_not_restart_new_connection(self):
        await self.manager.sync()
        old = self.manager.connections[1]
        self.settings[1] = make_settings(1, address="10.0.0.99")
        await self.manager.dispatch({"type": "machine.changed", "machine": 1})
        new = self.manager.connections[1]
        self.assertIsNot(new, old)
        new.stop.assert_not_awaited()
        new.start.assert_awaited_once()

    async def test_log_subscriptions(self):
        await self.manager.sync()
        connection = self.manager.connections[1]
        listener = await self.layer.new_channel()
        await self.manager.dispatch(
            {"type": "machine.logs.subscribe", "machine": 1, "channel": listener}
        )
        connection.set_log_streaming.assert_called_with(True)
        self.assertTrue(self.manager.has_log_listeners(1))

        await self.manager.forward_log(1, 3, "hello")
        message = await self.layer.receive(listener)
        self.assertEqual(message, {"type": "machine.log", "level": 3, "message": "hello"})

        await self.manager.dispatch(
            {"type": "machine.logs.unsubscribe", "machine": 1, "channel": listener}
        )
        connection.set_log_streaming.assert_called_with(False)
        self.assertFalse(self.manager.has_log_listeners(1))

    async def test_expired_log_subscriptions_are_dropped(self):
        await self.manager.sync()
        await self.manager.dispatch(
            {"type": "machine.logs.subscribe", "machine": 1, "channel": "listener"}
        )
        self.manager.log_listeners[1]["listener"] = 0
        self.manager._expire_log_listeners()
        self.assertFalse(self.manager.has_log_listeners(1))
        self.manager.connections[1].set_log_streaming.assert_called_with(False)

    async def test_status_is_published_to_the_machine_group(self):
        await self.manager.sync()
        listener = await self.layer.new_channel()
        await self.layer.group_add(protocol.machine_group(1), listener)
        await self.manager.publish_status(self.manager.connections[1])
        message = await self.layer.receive(listener)
        self.assertEqual(message["type"], "machine.state")
        self.assertEqual(message["status"]["state"], "standby")


@override_settings(ENABLE_CLIENT_API=True)
@patch("machines.esphome.manager.DeviceConnection", FakeConnection)
class BridgeTests(TestCase):
    """The website's side, talking to a running manager over the channel layer."""

    def setUp(self):
        self.layer = InMemoryChannelLayer()
        layer_patcher = patch("machines.esphome.bridge.get_channel_layer", return_value=self.layer)
        layer_patcher.start()
        self.addCleanup(layer_patcher.stop)
        self.manager = DeviceManager(
            channel_layer=self.layer, load_settings=lambda pk=None: {1: make_settings(1)}
        )

    async def run_manager(self):
        task = asyncio.create_task(self.manager.run())
        while not self.manager.connections:
            await asyncio.sleep(0)
        return task

    async def stop_manager(self, task):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_command_reaches_the_machine(self):
        task = await self.run_manager()
        try:
            await bridge.asend_command(1, "restart")
            self.manager.connections[1].run_command.assert_awaited_once_with("restart")
        finally:
            await self.stop_manager(task)

    async def test_status_round_trip(self):
        task = await self.run_manager()
        try:
            status = await bridge.aget_status(1)
            self.assertEqual(status["state"], "standby")
            self.assertEqual((await bridge.aget_status(2))["state"], "disconnected")
        finally:
            await self.stop_manager(task)

    async def test_failed_command_raises(self):
        task = await self.run_manager()
        try:
            with self.assertRaisesMessage(bridge.CommandFailed, "not connected"):
                await bridge.asend_command(2, "enable")
        finally:
            await self.stop_manager(task)

    async def test_version_round_trip(self):
        task = await self.run_manager()
        try:
            self.assertEqual(await bridge.aget_version(), running_version())
        finally:
            await self.stop_manager(task)

    async def test_unknown_command_is_refused_locally(self):
        with self.assertRaises(ValueError):
            await bridge.asend_command(1, "self_destruct")

    async def test_manager_not_running(self):
        with patch("machines.esphome.bridge.REQUEST_TIMEOUT", 0.05):
            with self.assertRaises(bridge.ManagerUnavailable):
                await bridge.arequest("machine.command", machine=1, command="enable", timeout=0.05)
        self.assertEqual((await bridge.aget_status(1))["state"], "disconnected")

    @override_settings(ENABLE_CLIENT_API=False)
    async def test_disabled_client_api(self):
        with self.assertRaises(bridge.ManagerUnavailable):
            await bridge.asend_command(1, "enable")


class MachineSignalTests(TestCase):
    @override_settings(ENABLE_CLIENT_API=True)
    def test_saving_a_machine_notifies_the_manager(self):
        with patch("machines.signals.bridge.notify_machine_changed") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                machine = Machine.objects.create(name="m", ip_address="10.0.0.1")
        notify.assert_called_once_with(machine.pk)

    def test_no_notification_when_client_api_disabled(self):
        with patch("machines.signals.bridge.notify_machine_changed") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                Machine.objects.create(name="m", ip_address="10.0.0.1")
        notify.assert_not_called()
