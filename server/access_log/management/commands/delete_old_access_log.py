from django.db import transaction
from django.core.management.base import BaseCommand

from access_log.tasks import delete_old_access_log


class Command(BaseCommand):
    help = "Deletes old access log entries"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        count = delete_old_access_log()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {count} old access log entries")
        )
