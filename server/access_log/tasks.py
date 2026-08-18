from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

from .models import (
    AccessLog,
    LOG_TYPE_ENABLED,
    LOG_TYPE_BOOTED,
    LOG_TYPE_DISABLED,
    LOG_TYPE_UNSUCCESSFUL,
)
from machines.models import Machine

logger = logging.getLogger(__name__)

duplicate_seconds_ago = (
    settings.ACCESS_LOG_DUPLICATE_SECONDS
    if hasattr(settings, "ACCESS_LOG_DUPLICATE_SECONDS")
    else 10
)
enabled_duration_max_seconds = (
    settings.ACCESS_LOG_ENABLED_DURATION_MAX_SECONDS
    if hasattr(settings, "ACCESS_LOG_ENABLED_DURATION_MAX_SECONDS")
    else 3600 * 5
)
delete_days = (
    settings.ACCESS_LOG_DELETE_DAYS
    if hasattr(settings, "ACCESS_LOG_DELETE_DAYS")
    else 0
)
anonymize_days = (
    settings.ACCESS_LOG_ANONYMIZE_DAYS
    if hasattr(settings, "ACCESS_LOG_ANONYMIZE_DAYS")
    else 0
)


@shared_task
def save_access_log(machine, token_id, log_type, timestamp=None):
    if not isinstance(machine, Machine):
        machine = Machine.objects.get(pk=machine)
    if log_type == LOG_TYPE_BOOTED and not machine.log_booted:
        return
    if log_type == LOG_TYPE_ENABLED and not machine.log_enabled:
        return
    if log_type == LOG_TYPE_DISABLED and not machine.log_disabled:
        return
    if log_type == LOG_TYPE_UNSUCCESSFUL and not machine.log_unsuccessful:
        return
    ago = timezone.now() - timedelta(seconds=duplicate_seconds_ago)
    if AccessLog.objects.filter(
        machine_id=machine.pk, token_id=token_id, type=log_type, timestamp__gte=ago
    ).exists():
        return
    enabled_duration = None
    log_timestamp = timestamp or timezone.now()
    if log_type == LOG_TYPE_DISABLED:
        last_enabled_log = AccessLog.objects.filter(
            machine_id=machine.pk, token_id=token_id, type=LOG_TYPE_ENABLED
        ).order_by("-timestamp").first()
        if last_enabled_log:
            enabled_duration = log_timestamp - last_enabled_log.timestamp
            if enabled_duration.total_seconds() < 0:
                logger.warning(
                    f"Access log for machine {machine.pk} and token {token_id} has negative enabled duration. Setting to None."
                )
                enabled_duration = None
            if enabled_duration and enabled_duration.total_seconds() > enabled_duration_max_seconds:
                logger.warning(
                    f"Access log for machine {machine.pk} and token {token_id} has enabled duration greater than {enabled_duration_max_seconds} seconds. Setting to None."
                )
                enabled_duration = None
    AccessLog.objects.create(
        machine_id=machine.pk,
        token_id=token_id,
        type=log_type,
        timestamp=log_timestamp,
        enabled_duration=enabled_duration,
    )


def find_old_access_log(days):
    return AccessLog.objects.filter(timestamp__lt=timezone.now() - timedelta(days=days))


@shared_task
def delete_old_access_log():
    if delete_days == 0:
        raise ImproperlyConfigured("ACCESS_LOG_DELETE_DAYS is not set")
    count = find_old_access_log(delete_days).delete()
    logger.debug(f"Deleted {count} old access log entries")
    return count


@shared_task
def anonymize_old_access_log():
    if anonymize_days == 0:
        raise ImproperlyConfigured("ACCESS_LOG_ANONYMIZE_DAYS is not set")

    count = find_old_access_log(anonymize_days).update(token=None)
    logger.debug(f"Anonymized {count} old access log entries")
    print(f"Anonymized {count} old access log entries")
    return count
