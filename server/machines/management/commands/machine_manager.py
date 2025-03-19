from django.core.management.base import BaseCommand
import asyncio
from aioesphomeapi import APIClient, UserService
import socket
import selectors
import types
import json

from machines.models import Machine

connections = {}


class ConnectionManager:
    device_state_key = None
    token_id_key = None
    mac_address_key = None
    error_message_key = None
    power_consumption_key = None
    
    reload_config_action_key = None
    restart_action_key = None
    enable_action_key = None
    disable_action_key = None

    is_enabled = False
    is_connected = False
    mac_address = None

    on_state_change = None

    def __init__(self, machine):
        self.machine = machine
        self.mac_address = machine.mac_address
        self.client = APIClient(
            machine.ip_address, 6053, None, noise_psk=machine.encryption_key
        )

    def send_command(self, command):
        if not self.is_connected:
            return
        key = None
        if command == "reload_config":
            key = self.reload_config_action_key
        elif command == "restart":
            key = self.restart_action_key
        elif command == "enable":
            key = self.enable_action_key
        elif command == "disable":
            key = self.disable_action_key
        if key is None:
            return
        service = UserService(name=command, key=key, args={})
        self.client.execute_service(service, {})

    async def change_callback(self, state):
        if self.on_state_change is not None:
            if self.device_state_key == state.key:
                await self.on_state_change({"state": state.state})

    async def setup_entities(self):
        entities = await self.client.list_entities_services()
        for entity in entities[0]:
            if entity.object_id == "device_state":
                self.device_state_key = entity.key
            elif entity.object_id == "token_id":
                self.token_id_key = entity.key
            elif entity.object_id == "error_message":
                self.error_message_key = entity.key
            elif entity.object_id == "current_power_consumption":
                self.power_consumption_key = entity.key
        for service in entities[1]:
            if service.name == "reload_config":
                self.reload_config_action_key = service.key
            elif service.name == "restart":
                self.restart_action_key = service.key
            elif service.name == "enable":
                self.enable_action_key = service.key
            elif service.name == "disable":
                self.disable_action_key = service.key

    async def connect(self):
        def change_callback(state):
            asyncio.ensure_future(self.change_callback(state))

        def on_stop(expected):
            self.is_connected = False
        
        await self.client.connect(login=True, on_stop=on_stop)
        self.is_connected = True
        await self.setup_entities()
        self.client.subscribe_states(change_callback)

    async def disconnect(self):
        self.is_connected = False
        if self.client is not None:
            await self.client.disconnect()


sel = selectors.DefaultSelector()


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


async def run_connect(machine):
    if machine.pk not in connections:
        connections[machine.pk] = ConnectionManager(machine)
        await asyncio.ensure_future(connections[machine.pk].connect())
        return


async def get_and_connect(pk):
    if pk in connections:
        return connections[pk]
    machine = await Machine.objects.aget(pk=pk)
    if machine is None or not machine.has_api:
        return
    await run_connect(machine)
    return connections[pk]


async def handle_client(client):
    loop = asyncio.get_event_loop()
    request = None
    while request != "quit":
        data = await loop.sock_recv(client, 1024)
        if data == b"":
            break
        print(data.decode())
        json_data = json.loads(data.decode())
        action = json_data["action"]
        pk = json_data["pk"]
        if pk is None or pk == "":
            break
        if action == "connect":
            await get_and_connect(pk)
        elif action == "enable":
            token_id = json_data["token_id"]
            await (await get_and_connect(pk)).enable_for(token_id)
        elif action == "disconnect":
            await (await get_and_connect(pk)).disconnect()
            connections.pop(pk)
        elif action == "reload_config":
            await (await get_and_connect(pk)).send_command("reload_config")
        elif action == "restart":
            await (await get_and_connect(pk)).send_command("restart")
        elif action == "status":
            if pk in connections and connections[pk].is_connected:
                if connections[pk].is_enabled:
                    await loop.sock_sendall(client, b"enabled")
                else:
                    await loop.sock_sendall(client, b"online")
            else:
                await loop.sock_sendall(client, b"disconnected")

    client.close()


async def handle_connections():
    async for machine in Machine.objects.exclude(ip_address__isnull=True):
        await run_connect(machine)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 6000))
    sock.listen()
    sock.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        client, _ = await loop.sock_accept(sock)
        loop.create_task(handle_client(client))


class Command(BaseCommand):
    help = "Handles connections to machines"

    def handle(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        try:
            asyncio.ensure_future(handle_connections())
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
