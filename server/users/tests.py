from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AdminChangePasswordViewTests(TestCase):
    def setUp(self):
        self.target = User.objects.create_user(email="target@example.com", password="old-password")
        self.url = reverse("users:admin_change_password", kwargs={"pk": self.target.pk})

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_user_without_permission_is_rejected(self):
        user = User.objects.create_user(email="nobody@example.com", password="pass")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_user_with_permission_can_change_password(self):
        user = User.objects.create_user(email="admin@example.com", password="pass")
        user.user_permissions.add(
            Permission.objects.get(codename="change_rfidinguser")
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self.url,
            {"password1": "a-new-strong-password-1", "password2": "a-new-strong-password-1"},
        )
        self.assertEqual(response.status_code, 302)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password("a-new-strong-password-1"))
