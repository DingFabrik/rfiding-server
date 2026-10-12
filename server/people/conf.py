from django.conf import settings

PERSON_DEFAULT_LANGUAGE = getattr(settings, "PERSON_DEFAULT_LANGUAGE", settings.LANGUAGES[0][0])
PERSON_ENABLE_SLACK_EMAIL = getattr(settings, "PERSON_ENABLE_SLACK_EMAIL", True)
PERSON_ENABLE_EMAIL = getattr(settings, "PERSON_ENABLE_EMAIL", True)
PERSON_SLACK_TOKEN = getattr(settings, "PERSON_SLACK_TOKEN", None)
PERSON_DETAIL_KEY_VALID_HOURS = getattr(settings, "PERSON_DETAIL_KEY_VALID_HOURS", 24)
# Self-service login: a code and link are e-mailed to the person.
PERSON_LOGIN_CODE_VALID_MINUTES = getattr(settings, "PERSON_LOGIN_CODE_VALID_MINUTES", 15)
PERSON_LOGIN_CODE_MAX_ATTEMPTS = getattr(settings, "PERSON_LOGIN_CODE_MAX_ATTEMPTS", 5)
PERSON_LOGIN_CODE_RESEND_SECONDS = getattr(settings, "PERSON_LOGIN_CODE_RESEND_SECONDS", 60)
# How long a person stays signed in to their self-service page.
PERSON_SESSION_VALID_HOURS = getattr(settings, "PERSON_SESSION_VALID_HOURS", 24)
# Qualifications expiring within this many days are flagged on the self-service page.
PERSON_PAGE_EXPIRY_WARNING_DAYS = getattr(settings, "PERSON_PAGE_EXPIRY_WARNING_DAYS", 30)
