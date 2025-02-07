from django.db import transaction
from django.core.management.base import BaseCommand

from access_log.tasks import anonymize_old_access_log


class Command(BaseCommand):
    help = "Remove token reference from old access log entries"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        count = anonymize_old_access_log()
        self.stdout.write(self.style.SUCCESS(f"Successfully anonymized {count} old access log entries"))
