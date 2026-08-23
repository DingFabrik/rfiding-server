from datetime import timedelta
from django.test import TestCase
from freezegun import freeze_time
from machines.models import Machine
from people.models import Person, Qualification


class QualificationExpiryTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_no_expiry_configured(self):
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        self.assertIsNone(qualification.compute_expires_at())

    def test_unused_expiry(self):
        self.machine.qualification_expiry_unused_days = 30
        self.machine.save()
        with freeze_time("2026-01-01 12:00:00"):
            qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        self.assertEqual(
            qualification.compute_expires_at(),
            qualification.created + timedelta(days=30),
        )

    def test_used_expiry_after_mark_used(self):
        self.machine.qualification_expiry_unused_days = 30
        self.machine.qualification_expiry_used_days = 90
        self.machine.save()
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        qualification.mark_used()
        self.assertIsNotNone(qualification.last_used)
        self.assertEqual(
            qualification.expires_at, qualification.last_used + timedelta(days=90)
        )
        self.assertIsNone(qualification.notified_at)

    def test_used_expiry_disabled_after_use(self):
        self.machine.qualification_expiry_unused_days = 30
        self.machine.save()
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        qualification.mark_used()
        self.assertIsNone(qualification.expires_at)
