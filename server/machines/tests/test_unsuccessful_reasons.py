from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from access_log.models import AccessLog, LOG_TYPE_UNSUCCESSFUL, UnsuccessfulReason
from machines.models import Machine
from people.models import Person, Qualification
from space.models import SpaceState
from tokens.models import Token


class UnsuccessfulReasonLoggingTests(APITestCase):
    url = reverse("api:v2:machine_check")
    machine_param = "mac_address"
    supports_compartments = True

    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            log_unsuccessful=True,
        )
        self.person = Person.objects.create(name="test", email="test@example.com")
        self.token = Token.objects.create(serial="456", person=self.person)

    def check(self, token_uid="456", **params):
        return self.client.get(
            self.url,
            {self.machine_param: "aabbccddeeff", "tokenUid": token_uid, **params},
            format="json",
        )

    def assertLogged(self, reason, token=None):
        log = AccessLog.objects.get(type=LOG_TYPE_UNSUCCESSFUL)
        self.assertEqual(log.unsuccessful_reason, reason)
        self.assertEqual(log.token, token)

    # Unknown and inactive tokens get the same response as a known token without
    # access, so the API can't be used to probe which serials exist.
    def test_unknown_token(self):
        response = self.check(token_uid="999")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "No Access!")
        self.assertLogged(UnsuccessfulReason.UNKNOWN_TOKEN)

    def test_inactive_token(self):
        self.token.is_active = False
        self.token.save()
        response = self.check()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "No Access!")
        self.assertLogged(UnsuccessfulReason.INACTIVE_TOKEN, self.token)

    def test_unknown_compartment(self):
        if not self.supports_compartments:
            self.skipTest("API version has no compartments")
        response = self.check(compartmentID="7")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertLogged(UnsuccessfulReason.UNKNOWN_COMPARTMENT)

    def test_lock_group(self):
        self.machine.type = "lock_group"
        self.machine.save()
        self.check()
        self.assertLogged(UnsuccessfulReason.LOCK_GROUP)

    def test_holiday(self):
        self.machine.allowed_on_holidays = False
        self.machine.save()
        with patch("machines.api.common.is_today_holiday", return_value=True):
            self.check()
        self.assertLogged(UnsuccessfulReason.HOLIDAY)

    def test_outside_hours(self):
        with patch.object(Machine, "get_valid_end_time_for_machine", return_value=None):
            self.check()
        self.assertLogged(UnsuccessfulReason.OUTSIDE_HOURS)

    def test_not_qualified(self):
        response = self.check()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "No Access!")
        self.assertLogged(UnsuccessfulReason.NOT_QUALIFIED, self.token)

    def test_qualification_blocked(self):
        Qualification.objects.create(
            machine=self.machine, person=self.person, permission_level="never"
        )
        self.check()
        self.assertLogged(UnsuccessfulReason.QUALIFICATION_BLOCKED, self.token)

    def test_qualification_expired(self):
        Qualification.objects.create(
            machine=self.machine,
            person=self.person,
            permission_level="always",
            expired=timezone.now(),
        )
        self.check()
        self.assertLogged(UnsuccessfulReason.QUALIFICATION_EXPIRED, self.token)

    def test_maintenance(self):
        self.machine.state = Machine.MachineStatus.MAINTENANCE
        self.machine.save()
        response = self.check()
        self.assertEqual(response.data["error"], "Machine in maintenance")
        self.assertLogged(UnsuccessfulReason.MAINTENANCE, self.token)

    def test_machine_blocked(self):
        self.machine.needs_qualification = False
        self.machine.permission_level = "never"
        self.machine.save()
        response = self.check()
        self.assertEqual(response.data["error"], "No Access!")
        self.assertLogged(UnsuccessfulReason.MACHINE_BLOCKED, self.token)

    def test_space_closed(self):
        Qualification.objects.create(machine=self.machine, person=self.person)
        SpaceState.objects.create(is_open=False)
        self.check()
        self.assertLogged(UnsuccessfulReason.SPACE_CLOSED, self.token)

    def test_internal_error(self):
        with patch("machines.api.common.check_access", side_effect=RuntimeError("boom")):
            self.check()
        self.assertLogged(UnsuccessfulReason.INTERNAL_ERROR)

    def test_successful_access_has_no_reason(self):
        self.machine.needs_qualification = False
        self.machine.save()
        response = self.check()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(AccessLog.objects.filter(type=LOG_TYPE_UNSUCCESSFUL).exists())
        self.assertTrue(
            AccessLog.objects.filter(unsuccessful_reason__isnull=True).exists()
        )


class V1UnsuccessfulReasonLoggingTests(UnsuccessfulReasonLoggingTests):
    url = reverse("api:machine_check")
    machine_param = "machine"
    supports_compartments = False
