from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from people.models import Person


class PersonToggleActiveViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(
            name="test", email="test@example.com", is_active=True
        )
        self.url = reverse("people:toggle-active", kwargs={"pk": self.person.pk})

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.person.refresh_from_db()
        self.assertTrue(self.person.is_active)

    def test_post_toggles_active_state(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.person.refresh_from_db()
        self.assertFalse(self.person.is_active)
