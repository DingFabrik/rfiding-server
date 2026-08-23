from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import QUALIFICATION_EXPIRY_WARNING_DAYS, Qualification
from .notifications import send_qualification_expiration_notification


@shared_task
def expire_qualifications():
    """Refresh expiration dates and expire any qualification that is due."""
    now = timezone.now()
    expired_count = 0
    for qualification in Qualification.objects.filter(
        expired__isnull=True
    ).select_related("machine"):
        expires_at = qualification.compute_expires_at()
        update_fields = []
        if expires_at != qualification.expires_at:
            qualification.expires_at = expires_at
            update_fields.append("expires_at")
        if expires_at is not None and expires_at <= now:
            qualification.expired = now
            update_fields.append("expired")
            expired_count += 1
        if update_fields:
            qualification.save(update_fields=update_fields)
    return expired_count


@shared_task
def notify_expiring_qualifications(days_before=QUALIFICATION_EXPIRY_WARNING_DAYS):
    """Notify people whose qualification will expire within `days_before` days."""
    threshold = timezone.now() + timedelta(days=days_before)
    notified_count = 0
    for qualification in Qualification.objects.filter(
        expired__isnull=True,
        notified_at__isnull=True,
        expires_at__isnull=False,
        expires_at__lte=threshold,
    ).select_related("person", "machine"):
        sent_via = send_qualification_expiration_notification(qualification)
        if sent_via:
            qualification.notified_at = timezone.now()
            qualification.save(update_fields=["notified_at"])
            notified_count += 1
    return notified_count
