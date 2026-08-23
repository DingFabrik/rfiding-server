from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from machines.models import Machine
from people.models import Person, Qualification

User = get_user_model()


class MachineAutocompleteViewTests(TestCase):
    url = reverse("machines:autocomplete")

    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="laser1", name="Laser Cutter"
        )

    def test_requires_permission(self):
        self.client.logout()
        response = self.client.get(self.url, {"term": "Laser"})
        self.assertEqual(response.status_code, 403)

    def test_empty_term_returns_no_results(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data, [])

    def test_matches_by_name(self):
        response = self.client.get(self.url, {"term": "Laser"})
        self.assertEqual(
            response.data, [{"value": self.machine.id, "label": "Laser Cutter"}]
        )

    def test_matches_by_hostname(self):
        response = self.client.get(self.url, {"term": "laser1"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["value"], self.machine.id)

    def test_result_limit(self):
        for i in range(25):
            Machine.objects.create(
                mac_address=f"aa:bb:cc:dd:ee:{i:02x}", hostname=f"m{i}", name=f"Term{i}"
            )
        response = self.client.get(self.url, {"term": "Term"})
        self.assertEqual(len(response.data), 20)


class QualifyableMachineAutocompleteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(name="Alice", email="alice@example.com")
        self.instructor = Person.objects.create(name="Bob", email="bob@example.com")
        self.url = reverse(
            "machines:autocomplete-qualifyable", kwargs={"person": self.person.pk}
        )

    def test_requires_permission(self):
        self.client.logout()
        response = self.client.get(self.url, {"term": "Laser"})
        self.assertEqual(response.status_code, 403)

    def test_excludes_inactive_and_non_qualifying_machines(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01",
            hostname="m1",
            name="Laser Needs Qualification",
            needs_qualification=True,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02",
            hostname="m2",
            name="Laser No Qualification Needed",
            needs_qualification=False,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:03",
            hostname="m3",
            name="Laser Inactive",
            needs_qualification=True,
            state=Machine.MachineStatus.INACTIVE,
        )

        response = self.client.get(self.url, {"term": "Laser"})
        labels = [m["label"] for m in response.data]
        self.assertEqual(len(labels), 1)
        self.assertIn("m1", labels[0])

    def test_excludes_machines_person_already_qualified_on(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01",
            hostname="m1",
            name="Laser",
            needs_qualification=True,
        )
        Qualification.objects.create(person=self.person, machine=machine)

        response = self.client.get(self.url, {"term": "Laser"})
        self.assertEqual(response.data, [])

    def test_includes_instructors_for_each_machine(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01",
            hostname="m1",
            name="Laser",
            needs_qualification=True,
        )
        Qualification.objects.create(
            person=self.instructor, machine=machine, is_instructor=True
        )

        response = self.client.get(self.url, {"term": "Laser"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["instructors"],
            [{"value": self.instructor.pk, "label": "Bob"}],
        )
