from django.urls import reverse
from freezegun import freeze_time
from machines.models import Machine, MachineTimes
from rest_framework import status
from rest_framework.test import APITestCase

from space.models import SpaceState
from tokens.models import Token
from people.models import Person, Qualification


class CheckMachineTests(APITestCase):
    url = reverse("api:machine_check")

    def test_missing_machine(self):
        """
        Ensure it errors if machine is not passed
        """
        data = {"tokenUid": "123"}
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fixes_mac_address(self):
        data = {"machine": "aa:bb:cc:dd:ee:ff", "tokenUid": "123"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            is_active=False,
        )
        machine.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Machine is restricted")

    def test_missing_token(self):
        """
        Ensure it errors if token is not passed
        """
        data = {"machine": "123"}
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_machine(self):
        """
        Ensure it errors if machine does not exist
        """
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_token(self):
        """
        Ensure it errors if token does not exist
        """
        data = {"machine": "aa:bb:cc:dd:ee:ff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_machine(self):
        """
        Ensure it errors if machine is inactive
        """
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test",
            name="test",
            is_active=False,
        )
        machine.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_token(self):
        """
        Ensure it errors if token is inactive
        """
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        token = Token.objects.create(serial="456", person=person, is_active=False)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_person(self):
        """
        Ensure it errors if token is inactive
        """
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(
            name="test", email="test@example.com", is_active=False
        )
        person.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_qualification(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["error"], "Person does not have access to machine"
        )

    def test_qualification(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        qualification = Qualification.objects.create(machine=machine, person=person)
        qualification.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], 1)

    def test_qualification_if_open_allows(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        qualification = Qualification.objects.create(machine=machine, person=person)
        qualification.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        state = SpaceState.objects.create(is_open=True)
        state.save()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], 1)

    def test_qualification_if_closed_disallows(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        qualification = Qualification.objects.create(machine=machine, person=person)
        qualification.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()
        state = SpaceState.objects.create(is_open=False)
        state.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["access"], 0)

    def test_qualification_if_always_alow_closed(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        qualification = Qualification.objects.create(
            machine=machine, person=person, permission_level="always"
        )
        qualification.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()
        state = SpaceState.objects.create(is_open=False)
        state.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], 1)

    @freeze_time("2024-04-16 12:00")
    def test_active_time(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        machinetime = MachineTimes.objects.create(
            machine=machine, weekdays="1,3", start_time="00:00", end_time="22:00"
        )
        machinetime.save()
        person = Person.objects.create(name="test", email="test@example.com")
        person.save()
        qualification = Qualification.objects.create(
            machine=machine, person=person, permission_level="always"
        )
        qualification.save()
        token = Token.objects.create(serial="456", person=person)
        token.save()

        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], 1)

    @freeze_time("2024-04-16 22:01")
    def test_inactive_time(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        machinetime = MachineTimes.objects.create(
            machine=machine, weekdays="0,1,3", start_time="00:00", end_time="22:00"
        )
        machinetime.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["access"], 0)

    @freeze_time("2024-04-16 22:00")
    def test_inactive_day(self):
        data = {"machine": "aabbccddeeff", "tokenUid": "456"}
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        machine.save()
        machinetime = MachineTimes.objects.create(
            machine=machine, weekdays="0,3", start_time="00:00", end_time="22:00"
        )
        machinetime.save()
        response = self.client.get(CheckMachineTests.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["access"], 0)
