from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models.functions import Trunc
from django.db.models import Count

from access_log.models import AccessLog


class Command(BaseCommand):
    help = "Deduplicate access log entries based on timestamp"

    @transaction.atomic
    def handle(self, *args, **options):
        (
            AccessLog.objects.annotate(time=Trunc("timestamp", "second"))
            .values("time", "token")
            .annotate(count=Count("time"))
            .filter(count__gt=1)
        )
