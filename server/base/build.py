import functools
import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac

SOURCE_ROOT = Path(__file__).resolve().parent.parent
DEPENDENCY_FILES = ("pyproject.toml", "poetry.lock")
SKIPPED_DIRECTORIES = {"__pycache__", "node_modules", "static", "static_src"}
TOKEN_SALT = "rfiding.health.version"


def current_version():
    if os.environ.get("RFIDING_BUILD_ID"):
        return os.environ["RFIDING_BUILD_ID"]
    digest = hashlib.sha256()
    files = []
    for directory, subdirectories, filenames in os.walk(SOURCE_ROOT):
        subdirectories[:] = sorted(
            d for d in subdirectories
            if d not in SKIPPED_DIRECTORIES and not d.startswith(".")
        )
        files += [Path(directory) / f for f in filenames if f.endswith(".py")]
    files += [SOURCE_ROOT.parent / f for f in DEPENDENCY_FILES]
    for path in sorted(files):
        if path.is_file():
            digest.update(str(path.relative_to(SOURCE_ROOT.parent)).encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()[:12]


@functools.cache
def running_version():
    return current_version()


def describe(version):
    return f"{settings.VERSION} ({version})"


def health_token():
    return salted_hmac(TOKEN_SALT, "version").hexdigest()


def is_valid_health_token(token):
    return bool(token) and constant_time_compare(token, health_token())
