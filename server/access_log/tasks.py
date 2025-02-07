from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import AccessLog

@shared_task
def save_access_log(machine_id, token_id, log_type):
    AccessLog.objects.create(
        machine__id=machine_id,
        token__id=token_id,
        type=log_type,
    )

def find_old_access_log(days):
    return AccessLog.objects.filter(timestamp__lt=timezone.now() - timedelta(days=days))

@shared_task
def delete_old_access_log():
    days = settings.ACCESS_LOG_DELETE_DAYS if hasattr(settings, "ACCESS_LOG_DELETE_DAYS") else 0
    if days == 0:
        raise ImproperlyConfigured("ACCESS_LOG_DELETE_DAYS is not set")
    return find_old_access_log(days).delete()

@shared_task
def anonymize_old_access_log():
    days = settings.ACCESS_LOG_ANONYMIZE_DAYS if hasattr(settings, "ACCESS_LOG_ANONYMIZE_DAYS") else 0
    if days == 0:
        raise ImproperlyConfigured("ACCESS_LOG_ANONYMIZE_DAYS is not set")
    return find_old_access_log(days).update(token=None)