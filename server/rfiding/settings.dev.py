import sys

from .base_settings import *

DEBUG = True

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
