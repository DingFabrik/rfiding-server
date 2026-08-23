from django.test import TestCase
from machines.models import Machine
from people.models import Person, Qualification


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
