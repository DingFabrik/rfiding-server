from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

MIN_SECRET_LENGTH = 16


@register()
def check_space_state_secret(app_configs, **kwargs):
    secret = getattr(settings, "SPACE_STATE_SECRET", "") or ""
    if not secret:
        return [
            Error(
                "SPACE_STATE_SECRET is empty.",
                hint="Set it to a long random value; clients need it to change the space state.",
                id="space.E001",
            )
        ]
    return []


@register(Tags.security, deploy=True)
def check_space_state_secret_strength(app_configs, **kwargs):
    secret = getattr(settings, "SPACE_STATE_SECRET", "") or ""
    if secret and len(secret) < MIN_SECRET_LENGTH:
        return [
            Warning(
                f"SPACE_STATE_SECRET is shorter than {MIN_SECRET_LENGTH} characters.",
                hint="Use a long random value, e.g. from `python -c 'import secrets; print(secrets.token_urlsafe(32))'`.",
                id="space.W001",
            )
        ]
    return []
