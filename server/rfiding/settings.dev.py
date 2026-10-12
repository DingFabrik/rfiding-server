import sys

from .base_settings import *

DEBUG = True

# Time zone of the space. Machine usage times, holidays and qualification dates
# are evaluated in this zone, so it must match where the machines are.
TIME_ZONE = "Europe/Berlin"

STATIC_ROOT = BASE_DIR / "/staticfiles/"

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": ["redis://localhost:6379/2"]},
    },
}

if "test" in sys.argv:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

CELERY_TASK_ALWAYS_EAGER = True

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
