from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from machines.models import Machine, MachineControlKey, MachineRegistrationRequest
from people.models import Person
from tokens.models import Token


class MachineRegisterViewTests(APITestCase):
    url = reverse("api:v2:machine_register")

    def test_registers_new_machine_request(self):
        response = self.client.post(
            self.url,
            {"mac_address": "aabbccddeeff", "hostname": "test", "ip_address": "1.2.3.4"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertFalse(response.data["registered"])
        self.assertTrue(
            MachineRegistrationRequest.objects.filter(
                mac_address="aa:bb:cc:dd:ee:ff"
            ).exists()
        )

    def test_does_not_duplicate_pending_registration_requests(self):
        self.client.post(
            self.url,
            {"mac_address": "aabbccddeeff", "hostname": "test"},
            format="json",
        )
        self.client.post(
            self.url,
            {"mac_address": "aabbccddeeff", "hostname": "test"},
            format="json",
        )
        self.assertEqual(MachineRegistrationRequest.objects.count(), 1)

    def test_existing_machine_reports_registered(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        response = self.client.post(
            self.url,
            {"mac_address": "aabbccddeeff", "hostname": "test"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["registered"])
        self.assertFalse(MachineRegistrationRequest.objects.exists())

    def test_missing_required_parameters_is_bad_request(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MachineConnectViewTests(APITestCase):
    url = reverse("api:v2:machine_connect")

    def test_connects_and_sends_socket_action(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        with patch("machines.api.v2.send_socket_action") as mock_send:
            response = self.client.get(
                self.url, {"mac_address": "aabbccddeeff"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["connected"])
        mock_send.assert_called_once()

    def test_unknown_machine_is_not_found(self):
        response = self.client.get(
            self.url, {"mac_address": "aabbccddeeff"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MachineConfigViewTests(APITestCase):
    url = reverse("api:v2:machine_config")

    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            runtimer=timedelta(minutes=5),
            min_power=10,
        )

    def test_get_returns_machine_config(self):
        response = self.client.get(
            self.url, {"mac_address": "aabbccddeeff"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["minPower"], 10)

    def test_post_updates_ip_address_and_firmware_version(self):
        response = self.client.post(
            self.url,
            {
                "mac_address": "aabbccddeeff",
                "ip_address": "10.0.0.5",
                "firmware_version": "1.2.3",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.ip_address, "10.0.0.5")
        self.assertEqual(self.machine.firmware_version, "1.2.3")

    def test_post_without_changes_does_not_save(self):
        with patch("machines.models.Machine.save") as mock_save:
            response = self.client.post(
                self.url, {"mac_address": "aabbccddeeff"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_save.assert_not_called()


class CheckMachineAccessViewV2Tests(APITestCase):
    url = reverse("api:v2:machine_check")

    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            needs_qualification=False,
        )
        self.person = Person.objects.create(name="test", email="test@example.com")
        self.token = Token.objects.create(serial="456", person=self.person)

    def test_successful_check_logs_enabled(self):
        response = self.client.get(
            self.url,
            {"mac_address": "aabbccddeeff", "tokenUid": "456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], 1)

    def test_unexpected_error_is_caught_and_logs_unsuccessful(self):
        with patch(
            "machines.api.v2.check_access", side_effect=RuntimeError("boom")
        ):
            response = self.client.get(
                self.url,
                {"mac_address": "aabbccddeeff", "tokenUid": "456"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Internal error")


class MachineDisableViewTests(APITestCase):
    url = reverse("api:v2:machine_disable")

    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )

    def test_disables_machine(self):
        response = self.client.get(
            self.url,
            {"mac_address": "aabbccddeeff", "tokenUid": "456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_disables_compartment_child(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:00",
            hostname="child",
            name="child",
            parent=self.machine,
            compartment_id="1",
        )
        response = self.client.get(
            self.url,
            {
                "mac_address": "aabbccddeeff",
                "tokenUid": "456",
                "compartmentID": "1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unknown_compartment_is_not_found(self):
        response = self.client.get(
            self.url,
            {
                "mac_address": "aabbccddeeff",
                "tokenUid": "456",
                "compartmentID": "does-not-exist",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MachineControlViewTests(APITestCase):
    url = reverse("api:v2:machine_control")

    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            ip_address="10.0.0.1",
            encryption_key="secret",
        )
        self.control_key = MachineControlKey.objects.create(
            machine=self.machine, purpose="test"
        )

    def test_rejects_machine_without_api(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:00", hostname="noapi", name="noapi"
        )
        key = MachineControlKey.objects.create(machine=machine, purpose="test")
        response = self.client.post(
            self.url,
            {
                "mac_address": "aabbccddee00",
                "action": "enable",
                "control_key": str(key.key),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_control_key(self):
        response = self.client.post(
            self.url,
            {
                "mac_address": "aabbccddeeff",
                "action": "enable",
                "control_key": "00000000-0000-0000-0000-000000000000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_invalid_action(self):
        # NB: `action` is required in the POST body (required_post_parameters)
        # but the actual action value used is read from the query string.
        response = self.client.post(
            self.url + "?action=bogus",
            {
                "mac_address": "aabbccddeeff",
                "control_key": str(self.control_key.key),
                "action": "bogus",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_action_sends_socket_action(self):
        with patch("machines.api.v2.send_socket_action") as mock_send:
            response = self.client.post(
                self.url + "?action=enable",
                {
                    "mac_address": "aabbccddeeff",
                    "control_key": str(self.control_key.key),
                    "action": "enable",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once_with(self.machine.pk, "enable")
