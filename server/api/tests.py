import secrets
from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.drainage import GENERATOR_STATS
from oauth2_provider.models import AccessToken
from rest_framework.test import APIClient

from users.models import RFIDingUser, UserWidget


def authenticate(client, user, scope="read write"):
    """Authenticate `client` as `user` with an OAuth2 access token of `scope`.

    `/api/rest/` only accepts OAuth2 tokens and checks their scope, so tests
    need a real token rather than a bare `force_authenticate(user)`.
    """
    token = AccessToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),
        expires=timezone.now() + timedelta(hours=1),
        scope=scope,
    )
    client.force_authenticate(user, token=token)
    return token


class UserApiPermissionTests(TestCase):
    def setUp(self):
        self.user = RFIDingUser.objects.create_user(
            email="staff@example.com", password="old-password"
        )
        self.client = APIClient()
        authenticate(self.client, self.user)

    def test_change_permission_cannot_grant_superuser(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_rfidinguser")
        )
        response = self.client.patch(
            f"/api/rest/v1/users/{self.user.pk}/",
            {"is_superuser": True, "is_staff": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)

    def test_superuser_can_grant_superuser(self):
        admin = RFIDingUser.objects.create_superuser(
            email="admin@example.com", password="pw"
        )
        authenticate(self.client, admin)
        response = self.client.patch(
            f"/api/rest/v1/users/{self.user.pk}/",
            {"is_superuser": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_superuser)

    def test_me_needs_no_model_permission(self):
        response = self.client.get("/api/rest/v1/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_change_own_password_needs_no_model_permission(self):
        response = self.client.post(
            f"/api/rest/v1/users/{self.user.pk}/change-password/",
            {"old_password": "old-password", "password": "new-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password"))

    def test_change_own_password_requires_old_password(self):
        for data in ({"password": "new"}, {"old_password": "wrong", "password": "new"}):
            response = self.client.post(
                f"/api/rest/v1/users/{self.user.pk}/change-password/", data, format="json"
            )
            self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-password"))

    def test_change_other_password_needs_change_permission(self):
        other = RFIDingUser.objects.create_user(
            email="other@example.com", password="pw"
        )
        response = self.client.post(
            f"/api/rest/v1/users/{other.pk}/change-password/",
            {"password": "new-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_change_permission_cannot_take_over_superuser(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["change_rfidinguser", "delete_rfidinguser"]
            )
        )
        admin = RFIDingUser.objects.create_superuser(
            email="admin@example.com", password="pw"
        )
        url = f"/api/rest/v1/users/{admin.pk}/"
        response = self.client.patch(url, {"password": "hijacked"}, format="json")
        self.assertEqual(response.status_code, 403)
        response = self.client.patch(
            url, {"email": "attacker@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            f"{url}change-password/", {"password": "hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("pw"))
        self.assertEqual(admin.email, "admin@example.com")

    def test_change_permission_cannot_take_over_more_privileged_user(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_rfidinguser")
        )
        group = Group.objects.create(name="admins")
        group.permissions.add(Permission.objects.get(codename="delete_rfidinguser"))
        other = RFIDingUser.objects.create_user(email="other@example.com", password="pw")
        other.groups.add(group)
        response = self.client.post(
            f"/api/rest/v1/users/{other.pk}/change-password/",
            {"password": "hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        other.refresh_from_db()
        self.assertTrue(other.check_password("pw"))

    def test_change_permission_cannot_reactivate_more_privileged_user(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_rfidinguser")
        )
        group = Group.objects.create(name="admins")
        group.permissions.add(Permission.objects.get(codename="delete_rfidinguser"))
        other = RFIDingUser.objects.create_user(
            email="other@example.com", password="pw", is_active=False
        )
        other.groups.add(group)
        response = self.client.patch(
            f"/api/rest/v1/users/{other.pk}/", {"is_active": True}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        other.refresh_from_db()
        self.assertFalse(other.is_active)

    def test_change_permission_can_edit_equally_privileged_user(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_rfidinguser")
        )
        other = RFIDingUser.objects.create_user(email="other@example.com", password="pw")
        response = self.client.patch(
            f"/api/rest/v1/users/{other.pk}/", {"name": "renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_change_group_cannot_grant_unheld_permissions(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_group"))
        group = Group.objects.create(name="mine")
        self.user.groups.add(group)
        escalated = Permission.objects.get(codename="delete_rfidinguser")
        response = self.client.patch(
            f"/api/rest/v1/groups/{group.pk}/",
            {"permissions": [escalated.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(group.permissions.exists())

    def test_change_group_cannot_edit_more_privileged_group(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_group"))
        group = Group.objects.create(name="admins")
        group.permissions.add(Permission.objects.get(codename="delete_rfidinguser"))
        response = self.client.patch(
            f"/api/rest/v1/groups/{group.pk}/", {"name": "renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_change_group_can_grant_held_permissions(self):
        held = Permission.objects.get(codename="change_group")
        self.user.user_permissions.add(held)
        group = Group.objects.create(name="mine")
        response = self.client.patch(
            f"/api/rest/v1/groups/{group.pk}/", {"permissions": [held.pk]}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_own_widgets_need_no_model_permission(self):
        response = self.client.post(
            "/api/rest/v1/widgets/", {"widget": UserWidget._meta.get_field("widget").choices[0][0]}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get("/api/rest/v1/widgets/")
        self.assertEqual(response.status_code, 200)


class SchemaTests(TestCase):
    """The OpenAPI schema is generated on request, so a view or serializer that
    drf-spectacular cannot handle only shows up when someone opens the docs."""

    def setUp(self):
        self.user = RFIDingUser.objects.create_superuser(
            email="admin@example.com", password="password"
        )
        self.client = APIClient()
        authenticate(self.client, self.user)
        # The machine-facing APIViews (api/v1, api/v2, space) have no serializers,
        # and drf-spectacular prints a warning for each straight to stderr.
        self.enterContext(GENERATOR_STATS.silence())

    def test_schema_covers_the_rest_api(self):
        response = self.client.get(reverse("rest:v1:schema"), {"format": "json"})
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for resource in ("machines", "people", "qualifications", "tokens", "access-logs"):
            self.assertIn(f"/api/rest/v1/{resource}/", paths)

    def test_docs_pages_render(self):
        for name in ("rest:v1:swagger-ui", "rest:v1:redoc"):
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
