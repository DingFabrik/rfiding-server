from django.urls import reverse
from machines.models import Machine
from rest_framework import status
from rest_framework.test import APITestCase

from tokens.models import Token
from people.models import Person, Qualification

class CheckMachineTests(APITestCase):
    url = reverse('api:machine_check')
    def test_missing_machine(self):
        """
        Ensure it errors if machine is not passed
        """
        data = {'tokenUid': '123'}
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_fixes_mac_address(self):
        data = {'machine': 'aa:bb:cc:dd:ee:ff', 'tokenUid': '123'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test', is_active=False)
        machine.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Machine is restricted')

    def test_missing_token(self):
        """
        Ensure it errors if token is not passed
        """
        data = {'machine': '123'}
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_machine(self):
        """
        Ensure it errors if machine does not exist
        """
        data = {'machine': 'aabbccddeeff', 'tokenUid': '456'}
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_token(self):
        """
        Ensure it errors if token does not exist
        """
        data = {'machine': 'aa:bb:cc:dd:ee:ff', 'tokenUid': '456'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test')
        machine.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_machine(self):
        """
        Ensure it errors if machine is inactive
        """
        data = {'machine': 'aabbccddeeff', 'tokenUid': '456'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test', is_active=False)
        machine.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_token(self):
        """
        Ensure it errors if token is inactive
        """
        data = {'machine': 'aabbccddeeff', 'tokenUid': '456'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test')
        machine.save()
        person = Person.objects.create(name='test', email='test@example.com')
        person.save()
        token = Token.objects.create(serial='456', person=person, is_active=False)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_inactive_person(self):
        """
        Ensure it errors if token is inactive
        """
        data = {'machine': 'aabbccddeeff', 'tokenUid': '456'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test')
        machine.save()
        person = Person.objects.create(name='test', email='test@example.com', is_active=False)
        person.save()
        token = Token.objects.create(serial='456', person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_qualification(self):
        data = {'machine': 'aabbccddeeff', 'tokenUid': '456'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test')
        machine.save()
        person = Person.objects.create(name='test', email='test@example.com')
        person.save()
        token = Token.objects.create(serial='456', person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Person does not have access to machine')

    def test_qualification(self):
        data = {'machine': 'aabbccddeeff', 'tokenUid': '456'}
        machine = Machine.objects.create(mac_address='aa:bb:cc:dd:ee:ff', hostname='test', name='test')
        machine.save()
        person = Person.objects.create(name='test', email='test@example.com')
        person.save()
        qualification = Qualification.objects.create(machine=machine, person=person)
        qualification.save()
        token = Token.objects.create(serial='456', person=person)
        token.save()
        response = self.client.get(CheckMachineTests.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['access'], 1)
