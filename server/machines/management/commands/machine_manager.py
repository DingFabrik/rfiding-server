from django.core.management.base import BaseCommand
import asyncio
from aioesphomeapi import APIClient, UserService
from aioesphomeapi.reconnect_logic import ReconnectLogic
import sys
import socket
import selectors
import types
from asgiref.sync import sync_to_async
import json

from machines.models import Machine
from machines.api.common import check_access

connections = {}

class ConnectionManager:
    is_enabled_key = None
    token_id_key = None
    
    is_enabled = False
    is_connected = False
    
    def __init__(self, machine):
        self.machine = machine
        self.client = APIClient(machine.ip_address, 6053, machine.encryption_key)
        
    async def enable_for(self, token_id):
        try:
            response = await sync_to_async(check_access)(self.machine, token_id)
            if "access" in response and response["access"] == 1:
                self.client.switch_command(self.is_enabled_key, state=True)
        except Exception as e:
            pass
        
    def send_command(self, command):
        if not self.is_connected:
            return
        service = UserService(name=command, key=1, args={})
        self.client.execute_service(service, {})
        
    async def change_callback(self, state):
        if state.key == self.token_id_key:
            token_id = state.state
            await self.enable_for(token_id)
    
    async def setup_entities(self):
        entities = await self.client.list_entities_services()
        for entity in entities[0]:
            if entity.object_id == "is_enabled_switch":
                self.is_enabled_key = entity.key
            if entity.object_id == "token_id":
                self.token_id_key = entity.key
    
    async def connect(self):        
        def change_callback(state):
            asyncio.ensure_future(self.change_callback(state))
        
        def on_connect():
            self.is_connected = True
            print("Connected to", self.machine.name)
            self.client.subscribe_states(change_callback)
            asyncio.ensure_future(self.setup_entities())
            
        def on_disconnect(is_expected):
            self.is_connected = False
            print("Disconnected from", self.machine.name, "expectedly" if is_expected else "unexpectedly")
        
        reconnect_logic = ReconnectLogic(client=self.client,
                                        on_connect=on_connect,
                                            on_disconnect=on_disconnect)
        await reconnect_logic.start()
        
    async def disconnect(self):
        self.is_connected = False
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
    await run_connect(machine)
    return connections[pk]

async def handle_client(client):
    loop = asyncio.get_event_loop()
    request = None
    while request != 'quit':
        data = await loop.sock_recv(client, 1024)
        if data == b'':
            break
        print(data.decode())
        json_data = json.loads(data.decode())
        action = json_data["action"]
        pk = json_data["pk"]
        if pk is None or pk == '':
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