import sys
from pathlib import Path
import toml

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


VERSION = "unknown"
# adopt path to your pyproject.toml
pyproject_toml_file = BASE_DIR / "../pyproject.toml"
if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
    data = toml.load(pyproject_toml_file)
    # check project.version
    if "project" in data and "version" in data["project"]:
        VERSION = data["project"]["version"]
    # check tool.poetry.version
    elif (
        "tool" in data
        and "poetry" in data["tool"]
        and "version" in data["tool"]["poetry"]
    ):
        VERSION = data["tool"]["poetry"]["version"]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-35c6=m7c4nu++9cw5ipmxz$klg_8(rf%b1*1(%rvq&cqcml$cd"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "drf_spectacular",
    "oauth2_provider",
    "crispy_forms",
    "django_celery_results",
    "django_celery_beat",
    "auditlog",
    "axes",
    "access_log",
    "base",
    "firmware",
    "holidays",
    "locations",
    "machines",
    "people",
    "space",
    "tokens",
    "users",
    "comments",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "users.middleware.LanguageMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    # Must be last: turns axes lockouts into the lockout response.
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    # Must come first, so locked-out logins are rejected before checking the password.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Lock out a username from an IP after repeated failed logins.
# Locking by username+IP (not IP alone) means people sharing the space's network
# don't lock each other out, and an attacker can't lock a user out everywhere.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
# The login form posts the email as "username"; axes would otherwise look for
# a credential named after USERNAME_FIELD ("email") and record no username.
AXES_USERNAME_FORM_FIELD = "username"
# Behind a reverse proxy REMOTE_ADDR is the proxy, which would turn the
# username+IP lockout into a username-only one. Resolve the client address like
# DRF's throttles instead, honouring REST_FRAMEWORK["NUM_PROXIES"].
AXES_CLIENT_IP_CALLABLE = "base.client_ip.get_client_ip"

ROOT_URLCONF = "rfiding.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "space.processors.space_state_processor",
                "base.processors.menu_processor",
                "base.processors.version_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "rfiding.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Per-process and therefore NOT shared between web and Celery workers. Anything
# that must be consistent across processes (e.g. holidays.utils.is_today_holiday)
# needs a shared backend - settings.prod.py overrides this with Redis.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

LANGUAGES = [
    ("en", "English"),
    ("de", "Deutsch"),
]

TIME_ZONE = "UTC"

USE_I18N = True
TIME_FORMAT = "H:i"

USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "public/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.RFIDingUser"
LOGIN_REDIRECT_URL = "/"

INTERNAL_IPS = [
    "127.0.0.1",
]

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["api.permissions.DjangoModelPermissionsWithView"],
    # Session stays first so pre-existing session-authenticated dashboard-internal
    # DRF views (ajax autocomplete, etc.) keep their original 401-vs-403 behavior -
    # DRF picks authenticators[0].authenticate_header() for that, and OAuth2's header
    # would otherwise coerce every anonymous 403 into a 401. The new `/api/rest/`
    # viewsets pin `authentication_classes = [OAuth2Authentication]` explicitly
    # (see api.viewsets.base.OAuth2OnlyMixin) so they are OAuth2-only regardless of
    # this order.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "base.filtering.DRFFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.PageLengthPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Applied per view (OAuth2OnlyMixin, machine registration), not globally, so
    # the machine-facing access API isn't throttled.
    # Throttles identify anonymous clients by IP. With NUM_PROXIES unset DRF
    # trusts the client-supplied X-Forwarded-For, so anyone could dodge the
    # limits by sending a new value each time. 0 = use REMOTE_ADDR; behind a
    # reverse proxy set it to the number of proxies (see settings.prod.py).
    "NUM_PROXIES": 0,
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",
        "machine_register": "30/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Rfiding Admin API",
    "DESCRIPTION": "REST API covering the data and actions available in the Rfiding admin dashboard.",
    "VERSION": VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "ThemeColorEnum": "users.models.THEME_COLORS",
    },
}

OAUTH2_PROVIDER = {
    "SCOPES": {
        "read": "Read access to your account and the data it can see in the dashboard",
        "write": "Write access to perform dashboard actions",
    },
    "ACCESS_TOKEN_EXPIRE_SECONDS": 60 * 60 * 8,
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "daisyui"
CRISPY_TEMPLATE_PACK = "daisyui"

SPACE_STATE_SECRET = "12345"
SPACE_NAME = "Makerspace"
SPACE_CONTACT = "01234 / 123456"

# Maximum length of a token ID sent by a machine for an access check. Longer IDs
# are cut to this length before they are looked up and before they are saved as
# unknown tokens. Stored token serials are not affected. None disables it.
TOKEN_ID_MAX_LENGTH = None

ASGI_APPLICATION = "rfiding.asgi.application"

CELERY_RESULT_BACKEND = "django-db"


def filter_unknown_token(record):
    if record.msg.startswith("Unknown token used"):
        return True
    return False


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{name} {levelname} {asctime} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "filter_unknown_tokens": {
            "()": "django.utils.log.CallbackFilter",
            "callback": filter_unknown_token,
        },
    },
    "handlers": {
        "console": {
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "console_verbose": {
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "tokens.models": {
            "filters": ["filter_unknown_tokens"],
            "handlers": ["console_verbose", "mail_admins"],
            "level": "INFO",
        },
    },
}

# Tests deliberately trigger failures (lockouts, unreachable machines, raised
# exceptions) that would otherwise be printed to stderr by Python's last-resort
# handler. assertLogs still works, since it installs its own handler.
if "test" in sys.argv:
    LOGGING["handlers"]["null"] = {"class": "logging.NullHandler"}
    LOGGING["root"] = {"handlers": ["null"]}

CELERY_BROKER_URL = "redis://localhost:6379/0"
