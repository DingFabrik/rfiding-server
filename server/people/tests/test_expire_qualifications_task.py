from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from machines.models import Machine
from people.models import Person, Qualification
from people.tasks import expire_qualifications


class ExpireQualificationsTaskTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            qualification_expiry_unused_days=1,
        )
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_expires_due_qualification(self):
        with freeze_time(timezone.now() - timedelta(days=2)):
            qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        count = expire_qualifications()
        self.assertEqual(count, 1)
        qualification.refresh_from_db()
        self.assertIsNotNone(qualification.expired)

    def test_does_not_expire_fresh_qualification(self):
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        count = expire_qualifications()
        self.assertEqual(count, 0)
        qualification.refresh_from_db()
        self.assertIsNone(qualification.expired)

    def test_refreshes_expires_at_when_config_changes(self):
        self.machine.qualification_expiry_unused_days = None
        self.machine.save()
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        self.machine.qualification_expiry_unused_days = 30
        self.machine.save()
        expire_qualifications()
        qualification.refresh_from_db()
        self.assertIsNotNone(qualification.expires_at)
        self.assertIsNone(qualification.expired)
