from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.db import DatabaseError
from django.db.models import Q

EXPIRE_TASK = "people.tasks.expire_qualifications"
NOTIFY_TASK = "people.tasks.notify_expiring_qualifications"
NOTIFICATION_TYPE = "qualification_expiration"

# Backends that accept mail without delivering it.
NON_DELIVERING_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
}


def email_enabled():
    return getattr(settings, "PERSON_ENABLE_EMAIL", True)


def slack_enabled():
    return getattr(settings, "PERSON_ENABLE_SLACK_EMAIL", True)


@register(deploy=True)
def check_email_notifications(app_configs, **kwargs):
    if not email_enabled():
        return []
    errors = []
    if settings.EMAIL_BACKEND in NON_DELIVERING_EMAIL_BACKENDS:
        errors.append(
            Warning(
                f"Email notifications are enabled, but EMAIL_BACKEND ({settings.EMAIL_BACKEND}) does not deliver mail.",
                hint="Configure an SMTP backend, or set PERSON_ENABLE_EMAIL = False.",
                id="people.W001",
            )
        )
    if settings.DEFAULT_FROM_EMAIL == "webmaster@localhost":
        errors.append(
            Warning(
                "Email notifications are enabled, but DEFAULT_FROM_EMAIL is Django's placeholder 'webmaster@localhost'.",
                hint="Set DEFAULT_FROM_EMAIL to the address notifications should come from.",
                id="people.W002",
            )
        )
    return errors


@register(deploy=True)
def check_slack_notifications(app_configs, **kwargs):
    if slack_enabled() and not getattr(settings, "PERSON_SLACK_TOKEN", None):
        return [
            Warning(
                "Slack notifications are enabled, but PERSON_SLACK_TOKEN is not set, so sending them fails.",
                hint="Set PERSON_SLACK_TOKEN to a Slack bot token, or set PERSON_ENABLE_SLACK_EMAIL = False.",
                id="people.W003",
            )
        ]
    return []


@register(deploy=True)
def check_notification_templates(app_configs, **kwargs):
    if not (email_enabled() or slack_enabled()):
        return []
    templates = getattr(settings, "PERSON_NOTIFICATION_TEMPLATES", {})
    if NOTIFICATION_TYPE in templates or "default" in templates:
        return []
    return [
        Warning(
            f"PERSON_NOTIFICATION_TEMPLATES has no '{NOTIFICATION_TYPE}' template, so people "
            "are only told 'You have a new notification' when a qualification is about to expire.",
            hint=f"Add a '{NOTIFICATION_TYPE}' entry with 'email' (subject, body) and 'slack' (text) "
            "templates. They can use {{ machine_name }} and {{ expires_at }}.",
            id="people.W004",
        )
    ]


@register(Tags.database, deploy=True)
def check_expiry_tasks_scheduled(app_configs, databases=None, **kwargs):
    """Qualification expiry only happens if its Celery tasks are scheduled."""
    if not databases:
        return []
    from django_celery_beat.models import PeriodicTask

    from machines.models import Machine

    try:
        if not Machine.objects.filter(
            Q(qualification_expiry_unused_days__gt=0)
            | Q(qualification_expiry_used_days__gt=0)
        ).exists():
            return []
        scheduled = set(
            PeriodicTask.objects.filter(
                enabled=True, task__in=[EXPIRE_TASK, NOTIFY_TASK]
            ).values_list("task", flat=True)
        )
    except DatabaseError:
        # Not migrated yet; the migrate check reports that.
        return []
    return [
        Warning(
            f"Machines have qualification expiry configured, but the periodic task {task} is not scheduled.",
            hint="Add it as a periodic task in the admin and run `celery -A rfiding beat "
            "-S django`, or run `manage.py "
            f"{task.rsplit('.', 1)[1]}` from cron and silence this warning.",
            id=id,
        )
        for task, id in ((EXPIRE_TASK, "people.W005"), (NOTIFY_TASK, "people.W006"))
        if task not in scheduled
    ]

