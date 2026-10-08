import os

from django.core.exceptions import ImproperlyConfigured

from .base_settings import *


def required_env(name):
    value = os.environ.get(name, "")
    if not value:
        raise ImproperlyConfigured(f"The {name} environment variable must be set.")
    return value


# Production settings
DEBUG = False

# Generate with: python -c 'import secrets; print(secrets.token_urlsafe(50))'
SECRET_KEY = required_env("DJANGO_SECRET_KEY")

# Directory where static files will be served from. Should be accessible for your Webserver
STATIC_ROOT = "/var/www/example.com/static/"

# Set all hosts your deploy will be available from
ALLOWED_HOSTS = []

# Origins (scheme + host) that may submit forms, e.g. ["https://rfiding.example.com"]
CSRF_TRUSTED_ORIGINS = []

# HTTPS. If TLS is terminated by a reverse proxy, the proxy must set
# X-Forwarded-Proto (and strip it from client requests); otherwise remove
# SECURE_PROXY_SSL_HEADER, or SECURE_SSL_REDIRECT will redirect in a loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Number of reverse proxies in front of the app: rate limits then use the client
# address the (last) proxy appended to X-Forwarded-For. Set to 0 without a proxy.
REST_FRAMEWORK["NUM_PROXIES"] = 1
# Start low and raise to a year (31536000) once HTTPS is known to work everywhere.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False

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
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": ["redis://localhost:6379/2"]},
    },
}

ENABLE_CLIENT_API = False
# Set to False if your machines' firmware doesn't implement the server
# verification of the ESPHome native API (see the client docs).
ESPHOME_VERIFY_SERVER = True

# Address of the website, used by `manage.py check --deploy --tag services`
# to ask the web server which version it runs, e.g. "https://rfiding.example.com".
HEALTH_CHECK_URL = ""

# Configure your space
# Clients changing the space state must send this secret. An empty secret is
# rejected; generate one like the SECRET_KEY above.
SPACE_STATE_SECRET = required_env("SPACE_STATE_SECRET")
SPACE_NAME = ""
SPACE_CONTACT = ""

# Cut token IDs sent for access checks to this many characters, e.g. 8 to match
# 4-byte UIDs from legacy readers. Stored token serials are not affected.
TOKEN_ID_MAX_LENGTH = None
