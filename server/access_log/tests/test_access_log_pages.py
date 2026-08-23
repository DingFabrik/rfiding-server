from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from access_log.models import AccessLog, LOG_TYPE_ENABLED
from machines.models import Machine
from people.models import Person
from tokens.models import Token


class AccessLogPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.person = Person.objects.create(name="test", email="test@example.com")
        self.token = Token.objects.create(serial="456", person=self.person)
        self.log = AccessLog.objects.create(
            machine=self.machine, token=self.token, type=LOG_TYPE_ENABLED
        )

    def test_list_page(self):
        response = self.client.get(reverse("access_log:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Machine")
        self.assertContains(response, "Token")

    def test_for_machine_page_hides_machine_column(self):
        response = self.client.get(
            reverse("access_log:for-machine", kwargs={"machine": self.machine.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Go to machine")
        self.assertContains(response, "Token")
        self.assertNotContains(response, "<th>Machine</th>", html=True)

    def test_for_person_page_shows_machine_and_token(self):
        response = self.client.get(
            reverse("access_log:for-person", kwargs={"person": self.person.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Go to person")
        self.assertContains(response, "<th>Machine</th>", html=True)
        self.assertContains(response, "<th>Token</th>", html=True)

    def test_for_token_page_hides_token_column(self):
        response = self.client.get(
            reverse("access_log:for-token", kwargs={"token": self.token.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Go to token")
        self.assertContains(response, "<th>Machine</th>", html=True)
        self.assertNotContains(response, "<th>Token</th>", html=True)

    def test_for_machine_page_empty_state(self):
        other_machine = Machine.objects.create(
            mac_address="11:22:33:44:55:66", hostname="empty", name="empty"
        )
        response = self.client.get(
            reverse("access_log:for-machine", kwargs={"machine": other_machine.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "has not been used yet")
