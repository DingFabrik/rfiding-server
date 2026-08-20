from django.conf import settings

PERSON_DEFAULT_LANGUAGE = getattr(settings, "PERSON_DEFAULT_LANGUAGE", settings.LANGUAGES[0][0])
PERSON_ENABLE_SLACK_EMAIL = getattr(settings, "PERSON_ENABLE_SLACK_EMAIL", True)
PERSON_ENABLE_EMAIL = getattr(settings, "PERSON_ENABLE_EMAIL", True)