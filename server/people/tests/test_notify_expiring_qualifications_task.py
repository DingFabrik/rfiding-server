from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from machines.models import Machine
from people.models import Person, Qualification
from people.tasks import expire_qualifications, notify_expiring_qualifications


class NotifyExpiringQualificationsTaskTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            qualification_expiry_unused_days=5,
        )
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_notifies_qualification_expiring_soon(self):
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 1)
        qualification.refresh_from_db()
        self.assertIsNotNone(qualification.notified_at)

    def test_does_not_notify_twice(self):
        Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        notify_expiring_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 0)

    def test_does_not_notify_far_out_expiration(self):
        self.machine.qualification_expiry_unused_days = 365
        self.machine.save()
        Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 0)

    def test_does_not_notify_already_expired(self):
        with freeze_time(timezone.now() - timedelta(days=20)):
            Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 0)
