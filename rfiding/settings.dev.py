from .base_settings import *

DEBUG = True

STATIC_ROOT = BASE_DIR / "/staticfiles/"

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
