from celery import shared_task

from .models import AccessLog

@shared_task
def save_access_log(machine_id, token_id, log_type):
    AccessLog.objects.create(
        machine__id=machine_id,
        token__id=token_id,
        type=log_type,
   )