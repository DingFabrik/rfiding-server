from django.core.management.base import BaseCommand

from people.tasks import expire_qualifications


class Command(BaseCommand):
    help = "Expires qualifications that have passed their configured expiration time"

    def handle(self, *args, **kwargs):
        count = expire_qualifications()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully expired {count} qualifications")
        )
