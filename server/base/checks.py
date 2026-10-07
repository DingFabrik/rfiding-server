import json
import urllib.request
from urllib.parse import urljoin

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.checks import Error, Warning, register
from django.urls import reverse

from base import build

TAG = "services"
WEB_TIMEOUT = 5
CELERY_TIMEOUT = 2


def outdated(service, version, current, hint, id):
    return Error(
        f"{service} runs version {build.describe(version or 'unknown')}, "
        f"but the installed code is {build.describe(current)}.",
        hint=hint,
        id=id,
    )


@register(TAG, deploy=True)
def check_web_version(app_configs, **kwargs):
    base_url = getattr(settings, "HEALTH_CHECK_URL", "")
    if not base_url:
        return [
            Warning(
                "HEALTH_CHECK_URL is not set, so the web server's version is not checked.",
                hint="Set it to the address the website is served at, e.g. https://rfiding.example.com.",
                id="services.W001",
            )
        ]
    url = urljoin(base_url, reverse("health-version"))
    request = urllib.request.Request(url, headers={"X-Health-Token": build.health_token()})
    try:
        with urllib.request.urlopen(request, timeout=WEB_TIMEOUT) as response:
            version = json.load(response).get("version")
    except Exception as e:
        return [
            Error(
                f"The web server at {url} did not report its version: {e}",
                hint="Check that the web server is running. An HTTP 404 means it runs "
                "outdated code or a different SECRET_KEY.",
                id="services.E001",
            )
        ]
    current = build.current_version()
    if version != current:
        return [outdated("The web server", version, current, "Restart the web server.", "services.E002")]
    return []


@register(TAG, deploy=True)
def check_celery_version(app_configs, **kwargs):
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return []
    from rfiding.celery import app

    try:
        with app.connection_for_write() as connection:
            connection.ensure_connection(max_retries=1)
        replies = app.control.inspect(timeout=CELERY_TIMEOUT).rfiding_version()
    except Exception as e:
        return [
            Error(
                f"The Celery broker is not reachable: {e}",
                hint="Check CELERY_BROKER_URL and that Redis is running.",
                id="services.E003",
            )
        ]
    if not replies:
        return [
            Error(
                "No Celery worker is running.",
                hint="Start one with `celery -A rfiding worker`.",
                id="services.E004",
            )
        ]
    current = build.current_version()
    return [
        outdated(f"Celery worker {worker}", reply.get("version"), current, "Restart the Celery workers.", "services.E005")
        for worker, reply in sorted(replies.items())
        if not isinstance(reply, dict) or reply.get("version") != current
    ]


@register(TAG, deploy=True)
def check_machine_manager_version(app_configs, **kwargs):
    from machines.esphome import bridge

    if not bridge.is_enabled():
        return []
    try:
        version = async_to_sync(bridge.aget_version)()
    except bridge.CommandFailed:
        version = None
    except Exception as e:
        return [
            Error(
                f"The machine manager is not running: {e}",
                hint="Start it with `manage.py machine_manager`. CHANNEL_LAYERS must use "
                "Redis, so that it is shared between the processes.",
                id="services.E006",
            )
        ]
    current = build.current_version()
    if version != current:
        return [outdated("The machine manager", version, current, "Restart `manage.py machine_manager`.", "services.E007")]
    return []
