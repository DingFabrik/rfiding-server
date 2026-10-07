"""Supervises the connections to all machines and serves the website's requests."""

import asyncio
import logging
import time

from asgiref.sync import sync_to_async
from channels.exceptions import ChannelFull
from channels.layers import get_channel_layer
from django.db import close_old_connections

from machines.api.common import machine_config
from machines.models import Machine

from . import protocol
from .bridge import DISCONNECTED_STATUS
from .connection import CommandError, DeviceConnection, MachineSettings

logger = logging.getLogger(__name__)


class RequestFailed(Exception):
    pass


def managed_machines():
    """Machines that speak the native API: they have an encryption key and an IP."""
    return (
        Machine.objects.exclude(state=Machine.MachineStatus.INACTIVE)
        .exclude(encryption_key__isnull=True)
        .exclude(encryption_key="")
        .exclude(ip_address__isnull=True)
    )


def machine_settings(machine):
    return MachineSettings(
        pk=machine.pk,
        name=machine.name,
        address=machine.ip_address,
        encryption_key=machine.encryption_key,
        mac_address=machine.mac_address,
        api_key=machine.api_key or None,
        config=dict(machine_config(machine)),
    )


def load_machine_settings(machine_pk=None):
    """{pk: MachineSettings} of all managed machines, or only of machine_pk."""
    close_old_connections()
    try:
        machines = managed_machines()
        if machine_pk is not None:
            machines = machines.filter(pk=machine_pk)
        return {machine.pk: machine_settings(machine) for machine in machines}
    finally:
        close_old_connections()


class DeviceManager:
    def __init__(self, channel_layer=None, load_settings=load_machine_settings):
        self.layer = channel_layer or get_channel_layer()
        self.load_settings = load_settings
        self.connections = {}
        # {machine pk: {channel name: lease expiry}}
        self.log_listeners = {}
        self.channel = None
        self._tasks = set()
        self._sync_lock = asyncio.Lock()

    async def run(self):
        if self.layer is None:
            raise RuntimeError("The machine manager needs a channel layer (CHANNEL_LAYERS)")
        self.channel = await self.layer.new_channel()
        await self.layer.group_add(protocol.MANAGER_GROUP, self.channel)
        try:
            await self.sync()
            await asyncio.gather(self._receive_loop(), self._maintenance_loop())
        finally:
            await self.shutdown()

    async def shutdown(self):
        for task in list(self._tasks):
            task.cancel()
        connections = list(self.connections.values())
        self.connections = {}
        await asyncio.gather(
            *(connection.stop() for connection in connections), return_exceptions=True
        )
        if self.channel is not None:
            await self.layer.group_discard(protocol.MANAGER_GROUP, self.channel)

    # Keeping the connections in sync with the database

    async def sync(self, machine_pk=None):
        """Connects to new machines, reconnects changed ones, drops removed ones."""
        async with self._sync_lock:
            settings = await sync_to_async(self.load_settings, thread_sensitive=False)(
                machine_pk
            )
            stale = (
                set(self.connections) - set(settings)
                if machine_pk is None
                else {machine_pk} - set(settings)
            )
            for pk in stale:
                await self._remove(pk)
            for machine_settings in settings.values():
                await self._apply(machine_settings)

    async def _apply(self, settings):
        connection = self.connections.get(settings.pk)
        if connection is not None:
            if connection.settings.connection_params == settings.connection_params:
                old = connection.settings
                connection.settings = settings
                if old.config != settings.config:
                    self._spawn(connection.push_config())
                return
            await self._remove(settings.pk)
        connection = DeviceConnection(settings, self)
        self.connections[settings.pk] = connection
        logger.info("Managing %s", connection)
        await connection.start()

    async def _remove(self, pk):
        connection = self.connections.pop(pk, None)
        if connection is None:
            return
        logger.info("No longer managing %s", connection)
        await connection.stop()
        await self.publish_status(connection)

    async def _maintenance_loop(self):
        while True:
            await asyncio.sleep(protocol.RESYNC_INTERVAL)
            try:
                # Group memberships expire in the redis channel layer.
                await self.layer.group_add(protocol.MANAGER_GROUP, self.channel)
                self._expire_log_listeners()
                await self.sync()
            except Exception:
                logger.exception("Machine manager maintenance failed")

    # Requests from the website

    async def _receive_loop(self):
        while True:
            message = await self.layer.receive(self.channel)
            self._spawn(self.dispatch(message))

    async def dispatch(self, message):
        handler = {
            "machine.command": self._handle_command,
            "machine.status": self._handle_status,
            "machine.changed": self._handle_changed,
            "machine.logs.subscribe": self._handle_logs_subscribe,
            "machine.logs.unsubscribe": self._handle_logs_unsubscribe,
        }.get(message.get("type"))
        reply_channel = message.get("reply_channel")
        if handler is None:
            reply = {"ok": False, "error": f"Unknown request {message.get('type')}"}
        else:
            try:
                reply = {"ok": True, **(await handler(message) or {})}
            except (RequestFailed, CommandError) as e:
                reply = {"ok": False, "error": str(e)}
            except Exception:
                logger.exception("Handling %s failed", message.get("type"))
                reply = {"ok": False, "error": "Internal error"}
        if reply_channel:
            await self.layer.send(reply_channel, {"type": "machine.reply", **reply})

    def _connection(self, message):
        connection = self.connections.get(message.get("machine"))
        if connection is None:
            raise RequestFailed("Machine is not connected over the API")
        return connection

    async def _handle_command(self, message):
        await self._connection(message).run_command(message.get("command"))

    async def _handle_status(self, message):
        return {"status": self._connection(message).status()}

    async def _handle_changed(self, message):
        pk = message.get("machine")
        existing = self.connections.get(pk)
        await self.sync(pk)
        async with self._sync_lock:
            connection = self.connections.get(pk)
            if connection is not None and connection is existing and not connection.connected:
                await self._remove(pk)
                await self._apply(connection.settings)

    async def _handle_logs_subscribe(self, message):
        pk, channel = message.get("machine"), message.get("channel")
        self.log_listeners.setdefault(pk, {})[channel] = time.monotonic() + protocol.LOG_LEASE
        connection = self.connections.get(pk)
        if connection is not None:
            connection.set_log_streaming(True)

    async def _handle_logs_unsubscribe(self, message):
        pk = message.get("machine")
        self.log_listeners.get(pk, {}).pop(message.get("channel"), None)
        self._stop_unused_log_streams()

    def _expire_log_listeners(self):
        now = time.monotonic()
        for listeners in self.log_listeners.values():
            for channel, expiry in list(listeners.items()):
                if expiry < now:
                    del listeners[channel]
        self._stop_unused_log_streams()

    def _stop_unused_log_streams(self):
        for pk in [pk for pk, listeners in self.log_listeners.items() if not listeners]:
            del self.log_listeners[pk]
            connection = self.connections.get(pk)
            if connection is not None:
                connection.set_log_streaming(False)

    # Called by the connections

    def has_log_listeners(self, pk):
        return bool(self.log_listeners.get(pk))

    async def forward_log(self, pk, level, message):
        listeners = self.log_listeners.get(pk, {})
        for channel in list(listeners):
            try:
                await self.layer.send(
                    channel, {"type": "machine.log", "level": level, "message": message}
                )
            except ChannelFull:
                # Nobody is reading this channel anymore.
                listeners.pop(channel, None)

    async def publish_status(self, connection):
        if connection.pk in self.connections:
            status = connection.status()
        else:
            status = dict(DISCONNECTED_STATUS)
        await self.layer.group_send(
            protocol.machine_group(connection.pk),
            {"type": "machine.state", "status": status},
        )

    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task):
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("Machine manager task failed", exc_info=task.exception())
