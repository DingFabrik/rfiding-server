from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from machines.models import Machine
from people.models import Person, Qualification
from people.tasks import expire_qualifications, notify_expiring_qualifications


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
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        notify_expiring_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 0)

    def test_does_not_notify_far_out_expiration(self):
        self.machine.qualification_expiry_unused_days = 365
        self.machine.save()
        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 0)

    def test_does_not_notify_already_expired(self):
        with freeze_time(timezone.now() - timedelta(days=20)):
            qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        expire_qualifications()
        count = notify_expiring_qualifications()
        self.assertEqual(count, 0)


class PersonQualificationsTableTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            qualification_expiry_unused_days=3,
        )
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_detail_page_shows_expiration_column(self):
        Qualification.objects.create(machine=self.machine, person=self.person)
        response = self.client.get(
            reverse("people:detail", kwargs={"pk": self.person.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Expiration")

    def test_far_future_expiration_is_hidden(self):
        self.machine.qualification_expiry_unused_days = 365
        self.machine.save()
        Qualification.objects.create(
            machine=self.machine, person=self.person, permission_level="always"
        )
        response = self.client.get(
            reverse("people:detail", kwargs={"pk": self.person.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "text-warning")

    def test_qualifications_list_page_shows_expired_status(self):
        Qualification.objects.create(
            machine=self.machine, person=self.person, expired=timezone.now()
        )
        response = self.client.get(
            reverse("people:qualifications", kwargs={"pk": self.person.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "octagon-x")
        self.assertContains(response, "text-error")


class QualifyPersonFormTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            qualification_expiry_unused_days=3,
        )
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_create_form_hides_expiration_fields(self):
        from people.forms import QualifyPersonForm

        form = QualifyPersonForm(initial={"person": self.person.pk, "machine": self.machine.pk})
        for field_name in ("last_used", "expires_at", "expired", "notified_at"):
            self.assertNotIn(field_name, form.fields)

    def test_edit_form_disables_computed_fields_but_not_notified_at(self):
        from people.forms import QualifyPersonForm

        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        qualification.mark_used()
        form = QualifyPersonForm(instance=qualification)
        for field_name in ("last_used", "expires_at", "expired"):
            self.assertTrue(form.fields[field_name].disabled)
        self.assertFalse(form.fields["notified_at"].disabled)

    def test_edit_form_ignores_tampered_read_only_fields(self):
        from people.forms import QualifyPersonForm

        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        qualification.mark_used()
        original_expires_at = qualification.expires_at
        data = {
            "person": self.person.pk,
            "machine": self.machine.pk,
            "permission_level": qualification.permission_level,
            "expires_at": "2099-01-01 00:00:00",
        }
        form = QualifyPersonForm(data=data, instance=qualification)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.expires_at, original_expires_at)

    def test_edit_form_allows_setting_notified_at(self):
        from people.forms import QualifyPersonForm

        qualification = Qualification.objects.create(machine=self.machine, person=self.person)
        data = {
            "person": self.person.pk,
            "machine": self.machine.pk,
            "permission_level": qualification.permission_level,
            "notified_at": "2026-01-01 00:00:00",
        }
        form = QualifyPersonForm(data=data, instance=qualification)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertIsNotNone(saved.notified_at)
