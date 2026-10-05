from channels.security.websocket import OriginValidator
from django.conf import settings


class BrowserOriginValidator(OriginValidator):
    """Reject websocket handshakes whose Origin isn't one of ALLOWED_HOSTS.

    Unlike channels' stock validator, a handshake *without* an Origin header is
    allowed: browsers always send one, so cross-site websocket hijacking always
    carries an Origin, while non-browser clients (door sensors setting the space
    state, scripts) often don't send one at all.
    """

    def valid_origin(self, parsed_origin):
        if parsed_origin is None:
            return True
        return super().valid_origin(parsed_origin)


def AllowedHostsOriginValidator(application):
    """Same host list as channels' AllowedHostsOriginValidator, with the rule above."""
    allowed_hosts = settings.ALLOWED_HOSTS
    if settings.DEBUG and not allowed_hosts:
        allowed_hosts = ["localhost", "127.0.0.1", "[::1]"]
    return BrowserOriginValidator(application, allowed_hosts)
