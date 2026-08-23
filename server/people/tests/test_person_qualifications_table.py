from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from machines.models import Machine
from people.models import Person, Qualification


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
