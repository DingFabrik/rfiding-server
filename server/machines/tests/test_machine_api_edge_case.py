from django.urls import reverse
from machines.models import Machine
from rest_framework import status
from rest_framework.test import APITestCase


class MachineApiEdgeCaseTests(APITestCase):
    config_url = reverse("api:v2:machine_config")
    check_url = reverse("api:v2:machine_check")

    def test_non_string_mac_address_is_bad_request_not_500(self):
        response = self.client.post(
            self.config_url, {"mac_address": 12345}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_mac_address_is_bad_request_not_500(self):
        response = self.client.post(
            self.config_url,
            {"mac_address": ["aa:bb:cc:dd:ee:ff"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_token_does_not_500(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        data = {"mac_address": "aabbccddeeff", "tokenUid": "x" * 500}
        response = self.client.get(self.check_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
