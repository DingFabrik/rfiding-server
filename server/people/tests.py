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


class PersonNotifierTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.person_with_email = Person.objects.create(name="test", email="test@example.com")
        self.person_without_email = Person.objects.create(name="test2", email=None)

    def test_email_notifier_can_notify(self):
        from people.notifiers import EmailNotifier

        notifier = EmailNotifier()
        self.assertTrue(notifier.can_notify(self.person_with_email))
        self.assertFalse(notifier.can_notify(self.person_without_email))

    def test_email_notifier_uses_fallback_template(self):
        from django.core import mail

        from people.notifiers import EmailNotifier

        notifier = EmailNotifier()
        sent = notifier.send(self.person_with_email, "some_unconfigured_type")
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.person_with_email.name, mail.outbox[0].body)

    def test_slack_notifier_cannot_notify_without_contact_info(self):
        from people.notifiers import SlackNotifier

        notifier = SlackNotifier()
        self.assertFalse(notifier.can_notify(self.person_with_email))

    def test_notify_person_returns_channels_actually_sent(self):
        from people.notifications import notify_person

        sent_via = notify_person(self.person_with_email, "some_unconfigured_type")
        self.assertEqual(sent_via, ["email"])

    def test_notify_person_uses_configured_template(self):
        from django.core import mail
        from django.test import override_settings

        from people.notifiers import EmailNotifier

        templates = {
            "qualification_expiration": {
                "email": {
                    "subject": "Bye {{ machine_name }}",
                    "body": "{{ person_name }} loses access to {{ machine_name }} on {{ expires_at }}",
                },
            },
        }
        with override_settings(PERSON_NOTIFICATION_TEMPLATES=templates):
            notifier = EmailNotifier()
            notifier.send(
                self.person_with_email,
                "qualification_expiration",
                {"machine_name": "Laser Cutter", "expires_at": "2026-01-01"},
            )
        self.assertEqual(mail.outbox[0].subject, "Bye Laser Cutter")
        self.assertIn("Laser Cutter", mail.outbox[0].body)

    def test_send_qualification_expiration_notification(self):
        from django.core import mail

        qualification = Qualification.objects.create(
            machine=self.machine, person=self.person_with_email
        )
        from people.notifications import send_qualification_expiration_notification

        sent_via = send_qualification_expiration_notification(qualification)
        self.assertEqual(sent_via, ["email"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.machine.name, mail.outbox[0].body)


class PersonDetailKeyTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_generate_detail_key_sets_expiry(self):
        key = self.person.generate_detail_key()
        self.assertTrue(key)
        self.assertEqual(self.person.detail_key, key)
        self.assertTrue(self.person.detail_key_valid)
        expected_expiry = timezone.now() + timedelta(hours=24)
        self.assertAlmostEqual(
            self.person.detail_key_expires_at, expected_expiry, delta=timedelta(seconds=5)
        )

    def test_detail_key_invalid_when_expired(self):
        self.person.generate_detail_key()
        self.person.detail_key_expires_at = timezone.now() - timedelta(seconds=1)
        self.person.save()
        self.assertFalse(self.person.detail_key_valid)

    def test_detail_key_invalid_when_unset(self):
        self.assertFalse(self.person.detail_key_valid)

    def test_generate_detail_key_produces_unique_keys(self):
        key1 = self.person.generate_detail_key()
        other = Person.objects.create(name="other", email="other@example.com")
        key2 = other.generate_detail_key()
        self.assertNotEqual(key1, key2)


class PersonPublicDetailViewTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="test", email="test@example.com")

    def test_valid_key_shows_page(self):
        self.person.generate_detail_key()
        response = self.client.get(
            reverse("people:public-detail", kwargs={"key": self.person.detail_key})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test")

    def test_expired_key_returns_403(self):
        self.person.generate_detail_key()
        self.person.detail_key_expires_at = timezone.now() - timedelta(hours=1)
        self.person.save()
        response = self.client.get(
            reverse("people:public-detail", kwargs={"key": self.person.detail_key})
        )
        self.assertEqual(response.status_code, 403)

    def test_unknown_key_returns_404(self):
        response = self.client.get(
            reverse("people:public-detail", kwargs={"key": "does-not-exist"})
        )
        self.assertEqual(response.status_code, 404)
