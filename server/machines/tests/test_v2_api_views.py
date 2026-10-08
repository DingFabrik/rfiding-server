from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from machines.api.common import truncate_token_id
from machines.esphome import bridge
from machines.models import Machine, MachineControlKey, MachineRegistrationRequest
from people.models import Person
from tokens.models import Token, UnknownToken


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

    def test_connect_notifies_the_machine_manager(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        with patch("machines.api.v2.bridge.notify_machine_changed") as mock_send:
            response = self.client.get(
                self.url, {"mac_address": "aabbccddeeff"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["connected"])
        mock_send.assert_called_once_with(machine.pk)

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
        self.assertNotIn("compartments", response.data)

    def test_locker_config_lists_compartments(self):
        self.machine.type = Machine.MachineType.LOCK_GROUP
        self.machine.save()
        Machine.objects.create(
            name="Left", type="compartment", parent=self.machine, compartment_id="1"
        )
        Machine.objects.create(
            name="Right", type="compartment", parent=self.machine, compartment_id="2"
        )
        Machine.objects.create(name="No ID", type="compartment", parent=self.machine)
        response = self.client.get(
            self.url, {"mac_address": "aabbccddeeff"}, format="json"
        )
        self.assertEqual(
            response.data["compartments"],
            [{"id": "1", "name": "Left"}, {"id": "2", "name": "Right"}],
        )

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
            "machines.api.common.check_access", side_effect=RuntimeError("boom")
        ):
            response = self.client.get(
                self.url,
                {"mac_address": "aabbccddeeff", "tokenUid": "456"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Internal error")


    @override_settings(TOKEN_ID_MAX_LENGTH=8)
    def test_long_token_id_is_truncated_for_lookup(self):
        Token.objects.create(serial="04a1b2c3", person=self.person)
        response = self.client.get(
            self.url,
            {"mac_address": "aabbccddeeff", "tokenUid": "04A1B2C3D4E5F6"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], 1)

    @override_settings(TOKEN_ID_MAX_LENGTH=8)
    def test_unknown_long_token_id_is_saved_truncated(self):
        response = self.client.get(
            self.url,
            {"mac_address": "aabbccddeeff", "tokenUid": "04a1b2c3d4e5f6"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            list(UnknownToken.objects.values_list("serial", flat=True)), ["04a1b2c3"]
        )

    @override_settings(TOKEN_ID_MAX_LENGTH=8)
    def test_short_token_id_is_unchanged(self):
        response = self.client.get(
            self.url,
            {"mac_address": "aabbccddeeff", "tokenUid": "456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(TOKEN_ID_MAX_LENGTH=8)
    def test_stored_serials_are_not_truncated(self):
        token = Token.objects.create(serial="04a1b2c3d4e5f6", person=self.person)
        token.refresh_from_db()
        self.assertEqual(token.serial, "04a1b2c3d4e5f6")

    @override_settings(TOKEN_ID_MAX_LENGTH=None)
    def test_without_max_length_token_id_is_used_as_sent(self):
        self.client.get(
            self.url,
            {"mac_address": "aabbccddeeff", "tokenUid": "04a1b2c3d4e5f6"},
            format="json",
        )
        self.assertEqual(
            list(UnknownToken.objects.values_list("serial", flat=True)),
            ["04a1b2c3d4e5f6"],
        )


class TruncateTokenIdTests(SimpleTestCase):
    @override_settings(TOKEN_ID_MAX_LENGTH=8)
    def test_truncates_to_max_length(self):
        self.assertEqual(truncate_token_id("04a1b2c3d4e5f6"), "04a1b2c3")
        self.assertEqual(truncate_token_id("04a1b2c3"), "04a1b2c3")
        self.assertEqual(truncate_token_id("456"), "456")

    @override_settings(TOKEN_ID_MAX_LENGTH=None)
    def test_disabled_by_default(self):
        self.assertEqual(truncate_token_id("04a1b2c3d4e5f6"), "04a1b2c3d4e5f6")

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

    def test_valid_action_is_sent_to_the_machine_manager(self):
        with patch("machines.api.v2.bridge.send_command") as mock_send:
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

    def test_manager_unavailable_is_service_unavailable(self):
        response = self.client.post(
            self.url + "?action=enable",
            {
                "mac_address": "aabbccddeeff",
                "control_key": str(self.control_key.key),
                "action": "enable",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_failed_command_is_bad_gateway(self):
        with patch(
            "machines.api.v2.bridge.send_command",
            side_effect=bridge.CommandFailed("Machine is offline"),
        ):
            response = self.client.post(
                self.url + "?action=enable",
                {
                    "mac_address": "aabbccddeeff",
                    "control_key": str(self.control_key.key),
                    "action": "enable",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["error"], "Machine is offline")
