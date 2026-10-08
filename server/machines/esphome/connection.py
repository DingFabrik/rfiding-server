"""One persistent native API connection to one machine."""

import asyncio
import dataclasses
import json
import logging
import re

from aioesphomeapi import (
    APIClient,
    APIConnectionError,
    HomeassistantServiceCall,
    LogLevel,
    ReconnectLogic,
    SupportsResponseType,
)
from asgiref.sync import sync_to_async
from django.conf import settings as django_settings

from . import protocol
from .handlers import RequestError, handle_request

logger = logging.getLogger(__name__)

ACTION_TIMEOUT = 10

# Entities whose changes are pushed to the website.
STATUS_ENTITIES = {
    protocol.ENTITY_DEVICE_STATE,
    protocol.ENTITY_POWER,
    protocol.ENTITY_ERROR_MESSAGE,
    protocol.ENTITY_SERVER_VERIFIED,
}


class CommandError(Exception):
    """A command could not be carried out on the machine."""


@dataclasses.dataclass(frozen=True)
class MachineSettings:
    """What the manager needs to know about a machine, read from the database."""

    pk: int
    name: str
    address: str
    encryption_key: str
    mac_address: str | None
    api_key: str | None
    config: dict

    @property
    def connection_params(self):
        return (self.address, self.encryption_key, self.mac_address, self.api_key)


def parse_log_message(message):
    try:
        return re.sub(r"\x1b\[[0-9;]*m", "", message.decode("utf-8"))
    except UnicodeDecodeError:
        return message.hex()


class DeviceConnection:

    def __init__(self, settings, manager):
        self.settings = settings
        self.manager = manager
        self.connected = False
        self.verified = False
        self.verify_server = django_settings.ESPHOME_VERIFY_SERVER
        self.firmware_version = None
        self.entity_keys = {}
        self.services = {}
        self.states = {}
        self._signed_challenge = None
        self._unsubscribe_logs = None
        self._tasks = set()
        mac = (settings.mac_address or "").replace(":", "").replace("-", "").lower()
        self.client = APIClient(
            settings.address,
            protocol.API_PORT,
            None,
            client_info=protocol.CLIENT_INFO,
            noise_psk=settings.encryption_key,
            # Refuse to talk to another device that got this machine's address.
            expected_mac=mac or None,
        )
        self.reconnect_logic = ReconnectLogic(
            client=self.client,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )

    @property
    def pk(self):
        return self.settings.pk

    def __str__(self):
        return f"{self.settings.name} ({self.settings.address})"

    async def start(self):
        await self.reconnect_logic.start()

    async def stop(self):
        await self.reconnect_logic.stop()
        await self.client.disconnect()
        self._reset()

    def status(self):
        state = self.states.get(protocol.ENTITY_DEVICE_STATE) or "unknown"
        return {
            "connected": self.connected,
            # None: verification is turned off, so there is nothing to show.
            "verified": self.verified if self.verify_server else None,
            "state": state if self.connected else "disconnected",
            "power": self.states.get(protocol.ENTITY_POWER),
            "error_message": self.states.get(protocol.ENTITY_ERROR_MESSAGE),
            "firmware_version": self.firmware_version,
        }

    # Connection lifecycle

    async def _on_connect(self):
        device_info, entities, services = await self.client.device_info_and_list_entities()
        self.firmware_version = device_info.project_version or None
        self.entity_keys = {entity.key: entity.object_id for entity in entities}
        self.services = {service.name: service for service in services}
        self.states = {}
        self.verified = False
        self._signed_challenge = None
        self.connected = True
        self.client.subscribe_states(self._on_state)
        self.client.subscribe_service_calls(self._on_service_call)
        logger.info("Connected to %s", self)
        if self.manager.has_log_listeners(self.pk):
            self.set_log_streaming(True)
        if self.verify_server and protocol.ACTION_AUTHENTICATE not in self.services:
            logger.warning(
                "%s does not support server verification (no %s action)",
                self,
                protocol.ACTION_AUTHENTICATE,
            )
        self._spawn(self.push_config())
        self._spawn(self.manager.publish_status(self))

    async def _on_disconnect(self, expected_disconnect):
        logger.info("Disconnected from %s (expected: %s)", self, expected_disconnect)
        self._reset()
        await self.manager.publish_status(self)

    def _reset(self):
        self.connected = False
        self.verified = False
        self._unsubscribe_logs = None
        self._signed_challenge = None

    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task):
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("Task for %s failed", self, exc_info=task.exception())

    # Device -> server

    def _on_state(self, state):
        object_id = self.entity_keys.get(state.key)
        if object_id is None:
            return
        value = None if getattr(state, "missing_state", False) else state.state
        if object_id in self.states and self.states[object_id] == value:
            return
        self.states[object_id] = value
        if object_id == protocol.ENTITY_SERVER_VERIFIED:
            self.verified = bool(value)
        if object_id in (protocol.ENTITY_CHALLENGE, protocol.ENTITY_SERVER_VERIFIED):
            if not self.verified:
                self._spawn(self.authenticate())
        if object_id in STATUS_ENTITIES:
            self._spawn(self.manager.publish_status(self))

    def _on_service_call(self, call: HomeassistantServiceCall):
        if call.is_event or not call.service.startswith(protocol.REQUEST_PREFIX):
            return
        self._spawn(self._handle_request(call))

    async def _handle_request(self, call):
        data = {**call.data, **call.data_template}
        response = b""
        try:
            result = await sync_to_async(handle_request, thread_sensitive=False)(
                self.pk, call.service, data
            )
            success, error = True, ""
            response = json.dumps(result).encode()
        except RequestError as e:
            success, error = False, str(e)
        except Exception:
            logger.exception("Handling %s from %s failed", call.service, self)
            success, error = False, "Internal error"
        if not call.call_id:
            return
        try:
            self.client.send_homeassistant_action_response(
                call.call_id, success, error, response
            )
        except APIConnectionError:
            logger.warning("Could not answer %s from %s", call.service, self)

    def _on_log(self, message):
        self._spawn(
            self.manager.forward_log(
                self.pk, message.level, parse_log_message(message.message)
            )
        )

    # Server -> device

    async def call_action(self, name, data=None, timeout=ACTION_TIMEOUT):
        if not self.connected:
            raise CommandError("Machine is offline")
        service = self.services.get(name)
        if service is None:
            raise CommandError(f"Machine does not support {name}")
        data = data or {}
        if service.supports_response in (None, SupportsResponseType.NONE):
            return_response = None
        else:
            return_response = service.supports_response != SupportsResponseType.STATUS
        try:
            response = await self.client.execute_service(
                service, data, return_response=return_response, timeout=timeout
            )
        except TimeoutError:
            raise CommandError("Machine did not answer") from None
        except APIConnectionError as e:
            raise CommandError(str(e)) from None
        if response is not None and not response.success:
            raise CommandError(response.error_message or f"{name} failed")
        return response

    async def authenticate(self):
        """Proves to the device that it is connected to the rfiding server."""
        challenge = self.states.get(protocol.ENTITY_CHALLENGE)
        api_key = self.settings.api_key
        if (
            not self.verify_server
            or not self.connected
            or not challenge
            or challenge == self._signed_challenge
            or protocol.ACTION_AUTHENTICATE not in self.services
        ):
            return
        if not api_key:
            logger.warning("%s has no API key, so the server cannot verify itself", self)
            return
        self._signed_challenge = challenge
        try:
            await self.call_action(
                protocol.ACTION_AUTHENTICATE,
                {"signature": protocol.sign_challenge(api_key, challenge)},
            )
        except CommandError as e:
            logger.warning("%s rejected the server verification: %s", self, e)
            return
        self.verified = True
        logger.info("Verified as rfiding server on %s", self)
        await self.manager.publish_status(self)

    async def push_config(self):
        """Sends the current configuration, if the device accepts it over the API."""
        if not self.connected or protocol.ACTION_SET_CONFIG not in self.services:
            return False
        try:
            await self.call_action(
                protocol.ACTION_SET_CONFIG, {"config": json.dumps(self.settings.config)}
            )
        except CommandError as e:
            logger.warning("Could not push config to %s: %s", self, e)
            return False
        return True

    async def run_command(self, command):
        if command not in protocol.COMMANDS:
            raise CommandError(f"Unknown command {command}")
        if command == protocol.ACTION_RELOAD_CONFIG and await self.push_config():
            return
        await self.call_action(command)

    def set_log_streaming(self, enabled):
        if not self.connected:
            return
        if enabled and self._unsubscribe_logs is None:
            self._unsubscribe_logs = self.client.subscribe_logs(
                self._on_log, LogLevel.LOG_LEVEL_DEBUG, dump_config=True
            )
        elif not enabled and self._unsubscribe_logs is not None:
            self._unsubscribe_logs()
            self._unsubscribe_logs = None
            # Unsubscribing only drops the callback; this stops the device sending.
            self.client.subscribe_logs(lambda _: None, LogLevel.LOG_LEVEL_NONE)()
