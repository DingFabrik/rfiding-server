import logging

from channels.security.websocket import OriginValidator
from django.conf import settings

logger = logging.getLogger(__name__)


class BrowserOriginValidator(OriginValidator):
    """Reject websocket handshakes whose Origin isn't one of ALLOWED_HOSTS.

    Unlike channels' stock validator, a handshake *without* an Origin header is
    allowed: browsers always send one, so cross-site websocket hijacking always
    carries an Origin, while non-browser clients (door sensors setting the space
    state, scripts) often don't send one at all.

    The same goes for an Origin without a host, such as "file://" (the default of
    the arduinoWebSockets library used on ESP32s), "null" or an empty value.
    Browsers only send those from sandboxed or file: contexts, which count as
    cross-site, so the SameSite session cookie isn't sent and the connection is
    anonymous, just like a client without an Origin.
    """

    def valid_origin(self, parsed_origin):
        if parsed_origin is None or parsed_origin.hostname is None:
            return True
        if super().valid_origin(parsed_origin):
            return True
        logger.warning(
            "Rejected websocket handshake from origin %r, which is not in ALLOWED_HOSTS",
            parsed_origin.geturl(),
        )
        return False


def AllowedHostsOriginValidator(application):
    """Same host list as channels' AllowedHostsOriginValidator, with the rule above."""
    allowed_hosts = settings.ALLOWED_HOSTS
    if settings.DEBUG and not allowed_hosts:
        allowed_hosts = ["localhost", "127.0.0.1", "[::1]"]
    return BrowserOriginValidator(application, allowed_hosts)
