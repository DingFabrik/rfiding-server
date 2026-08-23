from django.test import override_settings
from django.urls import reverse
from machines.models import Machine
from rest_framework import status
from rest_framework.test import APITestCase
from tokens.models import Token
from people.models import Person, Qualification


class MachineApiKeyTests(APITestCase):
    v1_url = reverse("api:machine_check")
    v2_url = reverse("api:v2:machine_check")

    def setUp(self):
        self.person = Person.objects.create(name="test", email="test@example.com")
        Token.objects.create(serial="456", person=self.person)

    def _make_qualified_machine(self, **kwargs):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test", **kwargs
        )
        Qualification.objects.create(machine=machine, person=self.person)
        return machine

    def test_v2_rejects_missing_key_when_machine_has_key(self):
        self._make_qualified_machine(api_key="secret-key")
        data = {"mac_address": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v2_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_v2_rejects_wrong_key(self):
        self._make_qualified_machine(api_key="secret-key")
        data = {"mac_address": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v2_url, data, format="json", HTTP_API_KEY="wrong-key")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_v2_accepts_correct_key(self):
        self._make_qualified_machine(api_key="secret-key")
        data = {"mac_address": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v2_url, data, format="json", HTTP_API_KEY="secret-key")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_allows_no_key_when_machine_has_none(self):
        self._make_qualified_machine()
        data = {"mac_address": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v2_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(ENFORCE_API_KEYS=True)
    def test_v2_rejects_no_key_when_enforced_and_machine_has_none(self):
        self._make_qualified_machine()
        data = {"mac_address": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v2_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_v1_rejects_missing_key_when_machine_has_key(self):
        self._make_qualified_machine(api_key="secret-key")
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v1_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_v1_accepts_correct_key(self):
        self._make_qualified_machine(api_key="secret-key")
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v1_url, data, format="json", HTTP_API_KEY="secret-key")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(ENFORCE_API_KEYS=True)
    def test_v1_rejects_no_key_when_enforced_and_machine_has_none(self):
        self._make_qualified_machine()
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(self.v1_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
