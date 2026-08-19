from django.core.management.base import BaseCommand

from people.tasks import notify_expiring_qualifications


class Command(BaseCommand):
    help = "Notifies people whose qualifications will expire within the next 7 days"

    def handle(self, *args, **kwargs):
        count = notify_expiring_qualifications()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully notified {count} people of upcoming qualification expiration")
        )
