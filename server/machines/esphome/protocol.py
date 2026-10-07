import hashlib
import hmac

# Sent as the API client_info, so the device can recognise our connection.
CLIENT_INFO = "rfiding-server"
API_PORT = 6053

# Server -> machine actions
ACTION_AUTHENTICATE = "rfiding_authenticate"
ACTION_SET_CONFIG = "set_config"
ACTION_ENABLE = "enable"
ACTION_DISABLE = "disable"
ACTION_RESTART = "restart"
ACTION_RELOAD_CONFIG = "reload_config"

# Commands the website may send to a machine.
COMMANDS = (ACTION_ENABLE, ACTION_DISABLE, ACTION_RESTART, ACTION_RELOAD_CONFIG)

# Machine -> server requests (homeassistant.action names)
REQUEST_PREFIX = "rfiding."
REQUEST_CHECK_ACCESS = "rfiding.check_access"
REQUEST_CONFIG = "rfiding.config"
REQUEST_DISABLED = "rfiding.disabled"

# Device entities (object ids) the server reads.
ENTITY_DEVICE_STATE = "device_state"
ENTITY_POWER = "current_power_consumption"
ENTITY_ERROR_MESSAGE = "error_message"
ENTITY_TOKEN_ID = "token_id"
ENTITY_CHALLENGE = "rfiding_challenge"
ENTITY_SERVER_VERIFIED = "rfiding_server_verified"

AUTH_CONTEXT = b"rfiding-server:"


def sign_challenge(api_key, challenge):
    return hmac.new(
        api_key.encode(), AUTH_CONTEXT + challenge.encode(), hashlib.sha256
    ).hexdigest()


# Channel layer names used between the website and the manager process.
MANAGER_GROUP = "esphome-manager"


def machine_group(machine_pk):
    """Websocket consumers showing a machine's state join this group."""
    return f"esphome-machine-{machine_pk}"


LOG_LEASE_RENEW_INTERVAL = 30
LOG_LEASE = 90

RESYNC_INTERVAL = 60
