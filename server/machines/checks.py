from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.db import DatabaseError

IN_MEMORY_CHANNEL_LAYER = "channels.layers.InMemoryChannelLayer"


def client_api_enabled():
    return getattr(settings, "ENABLE_CLIENT_API", False)


def channel_layer_backend():
    return getattr(settings, "CHANNEL_LAYERS", {}).get("default", {}).get("BACKEND")


@register(deploy=True)
def check_client_api_channel_layer(app_configs, **kwargs):
    """The website and `manage.py machine_manager` talk through the channel layer."""
    if not client_api_enabled():
        return []
    if channel_layer_backend() in (None, IN_MEMORY_CHANNEL_LAYER):
        return [
            Error(
                "ENABLE_CLIENT_API is set, but CHANNEL_LAYERS is not shared between processes, "
                "so the website cannot reach the machine manager.",
                hint="Use channels_redis.core.RedisChannelLayer.",
                id="machines.E001",
            )
        ]
    return []


@register(Tags.database, deploy=True)
def check_native_api_machines(app_configs, databases=None, **kwargs):
    """Machines with an encryption key are only reachable through the machine manager."""
    if not databases or client_api_enabled():
        return []
    from .models import Machine

    try:
        count = Machine.objects.exclude(encryption_key__isnull=True).exclude(encryption_key="").count()
    except DatabaseError:
        return []
    if count:
        return [
            Warning(
                f"{count} machine(s) have an encryption key for the native API, but ENABLE_CLIENT_API "
                "is not set, so the website cannot show their state or send them commands.",
                hint="Set ENABLE_CLIENT_API = True and run `manage.py machine_manager`.",
                id="machines.W001",
            )
        ]
    return []
