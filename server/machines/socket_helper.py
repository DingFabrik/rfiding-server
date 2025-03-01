import socket
import json
from django.conf import settings
import logging

ENABLE = settings.ENABLE_CLIENT_API if hasattr(settings, "ENABLE_CLIENT_API") else False
SOCKET_IP = settings.SOCKET_IP if hasattr(settings, "SOCKET_IP") else "127.0.0.1"
SOCKET_PORT = settings.SOCKET_PORT if hasattr(settings, "SOCKET_PORT") else 6000

logger = logging.getLogger(__name__)


def send_socket_action(machine_pk, action):
    if not ENABLE:
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SOCKET_IP, SOCKET_PORT))
            message = {
                "action": action,
                "pk": machine_pk,
            }
            s.sendall(json.dumps(message).encode())
    except Exception as e:
        logger.error(f"Socket error: {e}")


def get_socket_data(machine_pk, action):
    if not ENABLE:
        return None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SOCKET_IP, SOCKET_PORT))
            message = {
                "action": action,
                "pk": machine_pk,
            }
            s.sendall(json.dumps(message).encode())
            data = s.recv(1024)
            return data.decode()
    except Exception as e:
        logger.error(f"Socket error: {e}")
        return None
