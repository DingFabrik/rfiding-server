from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from people.models import Person


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
