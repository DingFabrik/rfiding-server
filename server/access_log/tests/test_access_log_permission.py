from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from machines.models import Machine
from people.models import Person
from tokens.models import Token


class AccessLogPermissionTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.person = Person.objects.create(name="test", email="test@example.com")
        self.token = Token.objects.create(serial="456", person=self.person)
        self.urls = [
            reverse("access_log:list"),
            reverse("access_log:for-machine", kwargs={"machine": self.machine.pk}),
            reverse("access_log:for-person", kwargs={"person": self.person.pk}),
            reverse("access_log:for-token", kwargs={"token": self.token.pk}),
        ]

    def test_anonymous_user_is_rejected(self):
        for url in self.urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200, url)

    def test_user_without_permission_is_rejected(self):
        user = get_user_model().objects.create_user(email="nobody@example.com", password="pass")
        self.client.force_login(user)
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, url)

    def test_user_with_permission_is_allowed(self):
        from django.contrib.auth.models import Permission

        user = get_user_model().objects.create_user(email="staff@example.com", password="pass")
        user.user_permissions.add(Permission.objects.get(codename="view_accesslog"))
        self.client.force_login(user)
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
