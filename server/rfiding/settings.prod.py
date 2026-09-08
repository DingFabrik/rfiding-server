from .base_settings import *

# Production settings
DEBUG = False

# Change this before deploying!
SECRET_KEY = "CHANGE_ME"

# Directory where static files will be served from. Should be accessible for your Webserver
STATIC_ROOT = "/var/www/example.com/static/"

# Set all hosts your deploy will be available from
ALLOWED_HOSTS = []

# Shared across web and Celery workers, unlike the LocMemCache default. Point
# this at the same Redis you use for the Celery broker.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Configure your space
SPACE_STATE_SECRET = ""
SPACE_NAME = ""
SPACE_CONTACT = ""
