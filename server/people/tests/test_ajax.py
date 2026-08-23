from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from machines.models import Machine
from people.models import Person, Qualification

User = get_user_model()


class PersonAutocompleteViewTests(TestCase):
    url = reverse("people:autocomplete")

    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(name="Alice", email="alice@example.com")
        self.inactive = Person.objects.create(
            name="Bob", email="bob@example.com", is_active=False
        )

    def test_requires_permission(self):
        self.client.logout()
        anonymous_response = self.client.get(self.url, {"term": "Alice"})
        self.assertEqual(anonymous_response.status_code, 403)

    def test_empty_term_returns_no_results(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_matches_by_name(self):
        response = self.client.get(self.url, {"term": "Ali"})
        self.assertEqual(
            response.data, [{"value": self.person.id, "label": "Alice (alice@example.com)"}]
        )

    def test_matches_by_email(self):
        response = self.client.get(self.url, {"term": "alice@example"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["value"], self.person.id)

    def test_excludes_inactive_people(self):
        response = self.client.get(self.url, {"term": "Bob"})
        self.assertEqual(response.data, [])

    def test_result_limit(self):
        for i in range(25):
            Person.objects.create(name=f"Term{i}", email=f"term{i}@example.com")
        response = self.client.get(self.url, {"term": "Term"})
        self.assertEqual(len(response.data), 20)


class QualifyablePersonAutocompleteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.qualified = Person.objects.create(name="Qualified", email="q@example.com")
        Qualification.objects.create(person=self.qualified, machine=self.machine)
        self.unqualified = Person.objects.create(
            name="Unqualified", email="u@example.com"
        )
        self.url = reverse(
            "people:autocomplete-qualifyable", kwargs={"machine": self.machine.pk}
        )

    def test_excludes_already_qualified_people(self):
        response = self.client.get(self.url, {"term": "ualified"})
        labels = [r["label"] for r in response.data]
        self.assertNotIn("Qualified (q@example.com)", labels)
        self.assertIn("Unqualified (u@example.com)", labels)


class InstructorPersonAutocompleteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.instructor = Person.objects.create(name="Instructor", email="i@example.com")
        Qualification.objects.create(
            person=self.instructor, machine=self.machine, is_instructor=True
        )
        self.non_instructor = Person.objects.create(
            name="NonInstructor", email="n@example.com"
        )
        Qualification.objects.create(
            person=self.non_instructor, machine=self.machine, is_instructor=False
        )
        self.url = reverse(
            "people:autocomplete-instructor", kwargs={"machine": self.machine.pk}
        )

    def test_excludes_existing_instructors_only(self):
        response = self.client.get(self.url, {"term": "structor"})
        labels = [r["label"] for r in response.data]
        self.assertNotIn("Instructor (i@example.com)", labels)
        self.assertIn("NonInstructor (n@example.com)", labels)
