from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from api.tests import authenticate
from machines.models import Machine
from people.models import Person, Qualification
from users.models import RFIDingUser


def grant(user, app_label, codename):
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label=app_label, codename=codename)
    )


class OAuthScopeTests(TestCase):
    def setUp(self):
        self.user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")
        grant(self.user, "people", "view_person")
        grant(self.user, "people", "change_person")
        self.person = Person.objects.create(name="Ada", email="ada@example.com")
        self.client = APIClient()
        self.url = f"/api/rest/v1/people/{self.person.pk}/"

    def test_read_scope_can_read(self):
        authenticate(self.client, self.user, scope="read")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_read_scope_cannot_write(self):
        authenticate(self.client, self.user, scope="read")
        response = self.client.patch(self.url, {"name": "Changed"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.person.refresh_from_db()
        self.assertEqual(self.person.name, "Ada")

    def test_read_scope_cannot_call_write_actions(self):
        authenticate(self.client, self.user, scope="read")
        response = self.client.post(f"{self.url}toggle_active/")
        self.assertEqual(response.status_code, 403)
        self.person.refresh_from_db()
        self.assertTrue(self.person.is_active)

    def test_write_scope_cannot_read(self):
        authenticate(self.client, self.user, scope="write")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_read_write_scope_can_write(self):
        authenticate(self.client, self.user)
        response = self.client.patch(self.url, {"name": "Changed"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_read_scope_cannot_change_own_password(self):
        # change-password overrides get_permissions(); the scope must still apply.
        authenticate(self.client, self.user, scope="read")
        response = self.client.post(
            f"/api/rest/v1/users/{self.user.pk}/change-password/",
            {"old_password": "pw", "password": "a-new-long-passphrase-42"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class PersonSystemMaintainerTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Ada", email="ada@example.com")
        self.url = f"/api/rest/v1/people/{self.person.pk}/"
        self.client = APIClient()

    def test_change_person_cannot_make_system_maintainer(self):
        user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")
        grant(user, "people", "change_person")
        authenticate(self.client, user)
        response = self.client.patch(
            self.url,
            {"is_system_maintainer": True, "slack_conversation_id": "C123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.person.refresh_from_db()
        self.assertFalse(self.person.is_system_maintainer)
        self.assertIsNone(self.person.slack_conversation_id)

    def test_superuser_can_make_system_maintainer(self):
        admin = RFIDingUser.objects.create_superuser(email="admin@example.com", password="pw")
        authenticate(self.client, admin)
        response = self.client.patch(self.url, {"is_system_maintainer": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.person.refresh_from_db()
        self.assertTrue(self.person.is_system_maintainer)


class QualificationInstructorApiTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Ada", email="ada@example.com")
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        self.user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")
        grant(self.user, "people", "qualify_person")
        self.client = APIClient()
        authenticate(self.client, self.user)

    def qualify(self):
        return self.client.post(
            "/api/rest/v1/qualifications/",
            {
                "person": self.person.pk,
                "machine": self.machine.pk,
                "is_instructor": True,
                "is_maintainer": True,
            },
            format="json",
        )

    def test_qualify_person_cannot_appoint_instructor(self):
        self.assertEqual(self.qualify().status_code, 201)
        qualification = Qualification.objects.get()
        self.assertFalse(qualification.is_instructor)
        self.assertFalse(qualification.is_maintainer)

    def test_change_instructor_can_appoint_instructor(self):
        grant(self.user, "people", "change_instructor")
        self.user = RFIDingUser.objects.get(pk=self.user.pk)
        authenticate(self.client, self.user)
        self.assertEqual(self.qualify().status_code, 201)
        qualification = Qualification.objects.get()
        self.assertTrue(qualification.is_instructor)
        self.assertTrue(qualification.is_maintainer)

    def test_machine_qualify_action_respects_change_instructor(self):
        # The model permissions map any POST on the machine viewset to add_machine.
        grant(self.user, "machines", "add_machine")
        self.user = RFIDingUser.objects.get(pk=self.user.pk)
        authenticate(self.client, self.user)
        response = self.client.post(
            f"/api/rest/v1/machines/{self.machine.pk}/qualify/",
            {"person": self.person.pk, "is_instructor": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(Qualification.objects.get().is_instructor)


class AuditLogApiPermissionTests(TestCase):
    def setUp(self):
        self.user = RFIDingUser.objects.create_user(email="staff@example.com", password="pw")
        self.client = APIClient()

    def test_view_token_is_not_enough(self):
        grant(self.user, "tokens", "view_token")
        authenticate(self.client, self.user)
        self.assertEqual(self.client.get("/api/rest/v1/audit-log/").status_code, 403)

    def test_view_logentry_is_required(self):
        grant(self.user, "auditlog", "view_logentry")
        authenticate(self.client, self.user)
        self.assertEqual(self.client.get("/api/rest/v1/audit-log/").status_code, 200)


class OAuthPasswordGrantTests(TestCase):
    """django-axes wraps authenticate(); the OAuth password grant must keep working."""

    def setUp(self):
        from oauth2_provider.models import Application

        self.user = RFIDingUser.objects.create_user(
            email="staff@example.com", password="the-right-password"
        )
        self.application = Application.objects.create(
            name="test",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
            client_secret="client-secret",
            hash_client_secret=False,
        )

    def request_token(self, password):
        return self.client.post(
            "/api/rest/v1/oauth/token/",
            {
                "grant_type": "password",
                "username": "staff@example.com",
                "password": password,
                "client_id": self.application.client_id,
                "client_secret": "client-secret",
                "scope": "read",
            },
        )

    def test_password_grant_issues_token(self):
        response = self.request_token("the-right-password")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scope"], "read")

    def test_wrong_password_is_rejected(self):
        response = self.request_token("wrong")
        self.assertEqual(response.status_code, 400, response.content)


class UserPasswordValidationApiTests(TestCase):
    def setUp(self):
        self.admin = RFIDingUser.objects.create_superuser(
            email="admin@example.com", password="an-admin-passphrase-42"
        )
        self.client = APIClient()
        authenticate(self.client, self.admin)

    def test_create_rejects_weak_password(self):
        response = self.client.post(
            "/api/rest/v1/users/",
            {"email": "new@example.com", "name": "New", "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.assertFalse(RFIDingUser.objects.filter(email="new@example.com").exists())

    def test_change_password_rejects_weak_password(self):
        response = self.client.post(
            f"/api/rest/v1/users/{self.admin.pk}/change-password/",
            {"old_password": "an-admin-passphrase-42", "password": "password"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_cannot_change_own_password_without_old_one(self):
        response = self.client.patch(
            f"/api/rest/v1/users/{self.admin.pk}/",
            {"password": "a-new-long-passphrase-42"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("an-admin-passphrase-42"))
