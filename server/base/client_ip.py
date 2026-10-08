from rest_framework.settings import api_settings


def get_client_ip(request):
    """The client address, resolved like DRF's throttles but failing closed.

    Without a proxy (NUM_PROXIES = 0) this is REMOTE_ADDR. Behind NUM_PROXIES
    reverse proxies it is the address the outermost of them appended to
    X-Forwarded-For, so clients cannot pick their own address by sending the
    header themselves. Unlike DRF, an unset NUM_PROXIES (None) is treated as 0
    rather than trusting the whole header. Used by django-axes via
    AXES_CLIENT_IP_CALLABLE.
    """
    remote_addr = request.META.get("REMOTE_ADDR")
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    num_proxies = api_settings.NUM_PROXIES or 0
    if num_proxies <= 0 or not forwarded_for:
        return remote_addr
    addresses = [address.strip() for address in forwarded_for.split(",")]
    return addresses[-min(num_proxies, len(addresses))]
