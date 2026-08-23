from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from people.models import Person


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
