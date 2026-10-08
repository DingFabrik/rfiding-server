"""Regression tests for the findings in SECURITY_AUDIT.md."""

from unittest import mock

from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import Resolver404, resolve, reverse
from rest_framework.test import APITestCase

from base.websocket import AllowedHostsOriginValidator
from machines.models import Machine, MachineControlKey, MachineRegistrationRequest
from people.models import Person, Qualification
from space.consumers import SpaceStateConsumer
from tokens.models import Token
from users.models import RFIDingUser, UserWidget


def grant(user, app_label, codename):
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label=app_label, codename=codename)
    )
    # Drop the cached permissions.
    return RFIDingUser.objects.get(pk=user.pk)


class UniversalSearchTests(TestCase):
    url = reverse("search-universal")

    def setUp(self):
        self.person = Person.objects.create(name="Ada Lovelace", email="ada@example.com")
        self.token = Token.objects.create(serial="ADA-SERIAL", person=self.person)
        self.user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url, {"search": "ada"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_results_are_limited_by_view_permissions(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"search": "ada"})
        self.assertEqual(response.context["objects"], [])

        self.user = grant(self.user, "people", "view_person")
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"search": "ada"})
        self.assertEqual(response.context["objects"], [self.person])
        self.assertNotContains(response, "ADA-SERIAL")

    def test_missing_search_parameter_is_not_an_error(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)


class AuditLogPermissionTests(TestCase):
    url = reverse("auditlog")

    def setUp(self):
        self.user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")

    def test_view_token_is_not_enough(self):
        self.client.force_login(grant(self.user, "tokens", "view_token"))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_view_logentry_grants_access(self):
        self.client.force_login(grant(self.user, "auditlog", "view_logentry"))
        self.assertEqual(self.client.get(self.url).status_code, 200)


class RevokeQualificationRedirectTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Ada", email="ada@example.com")
        machine = Machine.objects.create(mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m")
        self.qualification = Qualification.objects.create(person=self.person, machine=machine)
        user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")
        self.client.force_login(grant(user, "people", "qualify_person"))
        self.url = reverse(
            "people:revoke-qualification",
            kwargs={"pk": self.person.pk, "qualification": self.qualification.pk},
        )

    def test_external_next_is_ignored(self):
        response = self.client.post(self.url + "?next=https://evil.example/")
        self.assertRedirects(
            response,
            reverse("people:detail", kwargs={"pk": self.person.pk}),
            fetch_redirect_response=False,
        )

    def test_local_next_is_followed(self):
        response = self.client.post(self.url + "?next=/machines/")
        self.assertRedirects(response, "/machines/", fetch_redirect_response=False)


class InstructorPermissionDashboardTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Ada", email="ada@example.com")
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="m",
            name="m",
            needs_qualification=True,
            state=Machine.MachineStatus.ACTIVE,
        )
        self.user = grant(
            RFIDingUser.objects.create_user(email="staff@example.com", password="pw"),
            "people",
            "qualify_person",
        )
        self.url = reverse("people:qualify", kwargs={"pk": self.person.pk})

    def qualify(self):
        return self.client.post(
            self.url,
            {
                "machine_ids": [self.machine.pk],
                "permission_level": "always",
                "is_instructor": "on",
                "is_maintainer": "on",
            },
        )

    def test_qualify_person_alone_cannot_appoint_instructor(self):
        self.client.force_login(self.user)
        self.assertEqual(self.qualify().status_code, 302)
        qualification = Qualification.objects.get()
        self.assertFalse(qualification.is_instructor)
        self.assertFalse(qualification.is_maintainer)

    def test_change_instructor_can_appoint_instructor(self):
        self.client.force_login(grant(self.user, "people", "change_instructor"))
        self.assertEqual(self.qualify().status_code, 302)
        qualification = Qualification.objects.get()
        self.assertTrue(qualification.is_instructor)
        self.assertTrue(qualification.is_maintainer)

    def test_edit_keeps_existing_instructor_flag_without_permission(self):
        qualification = Qualification.objects.create(
            person=self.person, machine=self.machine, is_instructor=True
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse(
                "people:edit-qualification",
                kwargs={"pk": self.person.pk, "qualification": qualification.pk},
            ),
            {
                "person": self.person.pk,
                "machine": self.machine.pk,
                "permission_level": "always",
            },
        )
        self.assertEqual(response.status_code, 302)
        qualification.refresh_from_db()
        self.assertTrue(qualification.is_instructor)
        self.assertEqual(qualification.permission_level, "always")


@override_settings(ALLOWED_HOSTS=["rfiding.example"], SPACE_STATE_SECRET="test-secret")
class WebsocketOriginTests(TransactionTestCase):
    async def connect(self, origin=None):
        headers = [(b"origin", origin)] if origin is not None else []
        communicator = WebsocketCommunicator(
            AllowedHostsOriginValidator(SpaceStateConsumer.as_asgi()),
            "/ws/space/status/",
            headers=headers,
        )
        connected, _ = await communicator.connect()
        await communicator.disconnect()
        return connected

    async def test_foreign_origin_is_rejected(self):
        with self.assertLogs("base.websocket", "WARNING") as logs:
            self.assertFalse(await self.connect(b"https://evil.example"))
        self.assertIn("https://evil.example", logs.output[0])

    async def test_sibling_subdomain_is_rejected(self):
        self.assertFalse(await self.connect(b"https://other.rfiding.example"))

    async def test_own_origin_is_accepted(self):
        self.assertTrue(await self.connect(b"https://rfiding.example"))

    async def test_non_browser_client_without_origin_is_accepted(self):
        self.assertTrue(await self.connect())

    async def test_origin_without_host_is_accepted(self):
        # arduinoWebSockets on ESP32s sends "file://" by default.
        for origin in [b"file://", b"null", b""]:
            with self.subTest(origin=origin):
                self.assertTrue(await self.connect(origin))


class LoginLockoutTests(TestCase):
    def setUp(self):
        RFIDingUser.objects.create_user(email="staff@example.com", password="the-right-password")

    def login(self, password, **headers):
        return self.client.post(
            reverse("login"), {"username": "staff@example.com", "password": password}, **headers
        )

    def test_repeated_failures_lock_the_account_out(self):
        for _ in range(5):
            self.login("wrong")
        self.login("the-right-password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_does_not_affect_other_users_on_the_same_network(self):
        RFIDingUser.objects.create_user(email="other@example.com", password="other-password")
        for _ in range(5):
            self.login("wrong")
        self.client.post(
            reverse("login"), {"username": "other@example.com", "password": "other-password"}
        )
        self.assertIn("_auth_user_id", self.client.session)

    def test_correct_password_works_before_the_limit(self):
        for _ in range(4):
            self.login("wrong")
        self.login("the-right-password")
        self.assertIn("_auth_user_id", self.client.session)


class LoginLockoutSpoofingTests(TestCase):
    """Without a configured proxy, X-Forwarded-For comes from the client and must be ignored."""

    def setUp(self):
        RFIDingUser.objects.create_user(email="staff@example.com", password="the-right-password")

    def login(self, password, forwarded_for):
        return self.client.post(
            reverse("login"),
            {"username": "staff@example.com", "password": password},
            HTTP_X_FORWARDED_FOR=forwarded_for,
        )

    def assert_spoofing_does_not_dodge_the_lockout(self):
        for i in range(5):
            self.login("wrong", f"10.0.0.{i}")
        self.login("the-right-password", "10.0.0.99")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_with_default_settings(self):
        self.assert_spoofing_does_not_dodge_the_lockout()

    @override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": None})
    def test_with_num_proxies_unset(self):
        # DRF itself would trust the whole header here.
        self.assert_spoofing_does_not_dodge_the_lockout()


@override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 1})
class LoginLockoutBehindProxyTests(TestCase):
    """Behind a reverse proxy every request comes from the proxy's address, so
    lockouts must use the client address the proxy put in X-Forwarded-For."""

    PROXY = "127.0.0.1"

    def setUp(self):
        RFIDingUser.objects.create_user(email="staff@example.com", password="the-right-password")

    def login(self, password, forwarded_for):
        return self.client.post(
            reverse("login"),
            {"username": "staff@example.com", "password": password},
            REMOTE_ADDR=self.PROXY,
            HTTP_X_FORWARDED_FOR=forwarded_for,
        )

    def test_failures_from_one_client_do_not_lock_out_another(self):
        for _ in range(5):
            self.login("wrong", "203.0.113.1")
        self.login("the-right-password", "203.0.113.2")
        self.assertIn("_auth_user_id", self.client.session)

    def test_failures_lock_out_the_client(self):
        for _ in range(5):
            self.login("wrong", "203.0.113.1")
        self.login("the-right-password", "203.0.113.1")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_spoofed_forwarded_for_does_not_dodge_the_lockout(self):
        # The client sends its own X-Forwarded-For; the proxy appends the real address.
        for i in range(5):
            self.login("wrong", f"10.0.0.{i}, 203.0.113.1")
        self.login("the-right-password", "10.0.0.99, 203.0.113.1")
        self.assertNotIn("_auth_user_id", self.client.session)


class DebugToolbarRouteTests(TestCase):
    def test_debug_route_is_not_mounted_without_debug(self):
        with self.assertRaises(Resolver404):
            resolve("/__debug__/render_panel/")


class UnvalidatedInputTests(TestCase):
    def setUp(self):
        self.admin = RFIDingUser.objects.create_superuser(email="admin@example.com", password="pw")
        self.client.force_login(self.admin)

    def test_machine_statistics_with_invalid_days(self):
        machine = Machine.objects.create(mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m")
        url = reverse("machines:statistics", kwargs={"pk": machine.pk})
        self.assertEqual(self.client.get(url, {"days": "abc"}).status_code, 200)

    def test_home_widgets_with_invalid_widget_id(self):
        UserWidget.objects.create(user=self.admin, widget="space_status", position=0)
        response = self.client.get(reverse("users:widgets:home"), {"widget_id": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["widgets"]), [])


class MachineApiInputTests(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_control_action_is_read_from_the_body(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="m",
            name="m",
            ip_address="10.0.0.1",
            encryption_key="secret",
        )
        key = MachineControlKey.objects.create(machine=machine, purpose="test")
        with mock.patch("machines.api.v2.bridge.send_command") as send:
            response = self.client.post(
                reverse("api:v2:machine_control"),
                {"mac_address": "aabbccddeeff", "action": "restart", "control_key": str(key.key)},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        send.assert_called_once_with(machine.pk, "restart")

    def test_register_ignores_invalid_ip_address(self):
        self.client.post(
            reverse("api:v2:machine_register"),
            {"mac_address": "aabbccddeeff", "hostname": "m", "ip_address": "not-an-ip"},
            format="json",
        )
        self.assertEqual(MachineRegistrationRequest.objects.get().ip_address, "127.0.0.1")

    def test_register_is_throttled(self):
        url = reverse("api:v2:machine_register")
        for i in range(30):
            response = self.client.post(
                url, {"mac_address": f"aabbccdd{i:04x}", "hostname": "m"}, format="json"
            )
            self.assertEqual(response.status_code, 202)
        response = self.client.post(
            url, {"mac_address": "aabbccddffff", "hostname": "m"}, format="json"
        )
        self.assertEqual(response.status_code, 429)

    def test_register_throttle_ignores_spoofed_forwarded_for(self):
        url = reverse("api:v2:machine_register")
        for i in range(31):
            response = self.client.post(
                url,
                {"mac_address": f"aabbccdd{i:04x}", "hostname": "m"},
                format="json",
                HTTP_X_FORWARDED_FOR=f"10.0.{i}.1",
            )
        self.assertEqual(response.status_code, 429)
