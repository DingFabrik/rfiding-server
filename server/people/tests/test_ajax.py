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
        self.assertEqual(anonymous_response.status_code, 302)

    def test_empty_term_returns_no_results(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["people"]), [])
        self.assertNotContains(response, "person-result-row")

    def test_matches_by_name(self):
        response = self.client.get(self.url, {"term": "Ali"})
        self.assertEqual(list(response.context["people"]), [self.person])
        self.assertContains(response, f'data-id="{self.person.id}"')
        self.assertContains(response, 'data-label="Alice (alice@example.com)"')

    def test_matches_by_email(self):
        response = self.client.get(self.url, {"term": "alice@example"})
        self.assertEqual(list(response.context["people"]), [self.person])

    def test_excludes_inactive_people(self):
        response = self.client.get(self.url, {"term": "Bob"})
        self.assertEqual(list(response.context["people"]), [])
        self.assertContains(response, "No matches.")

    def test_result_limit(self):
        for i in range(25):
            Person.objects.create(name=f"Term{i}", email=f"term{i}@example.com")
        response = self.client.get(self.url, {"term": "Term"})
        self.assertEqual(len(response.context["people"]), 20)


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
        self.assertNotContains(response, "Qualified (q@example.com)")
        self.assertContains(response, "Unqualified (u@example.com)")

    def test_ignores_malformed_selected_ids(self):
        response = self.client.get(
            self.url, {"term": "Unqualified", "person_ids": ["", "abc"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unqualified (u@example.com)")

    def test_excludes_already_selected_people(self):
        response = self.client.get(
            self.url, {"term": "Unqualified", "person_ids": [str(self.unqualified.pk)]}
        )
        self.assertNotContains(response, "Unqualified (u@example.com)")

    def test_requires_permission(self):
        self.client.logout()
        response = self.client.get(self.url, {"term": "ualified"})
        self.assertEqual(response.status_code, 302)
