from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def perm(codename):
    return Permission.objects.get(codename=codename)


class UserManagementEscalationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(email="manager@example.com", password="pw")
        self.manager.user_permissions.add(
            perm("view_rfidinguser"), perm("add_rfidinguser"), perm("change_rfidinguser")
        )
        self.client.force_login(self.manager)
        self.admin_group = Group.objects.create(name="admins")
        self.admin_group.permissions.add(perm("delete_rfidinguser"))

    def form_data(self, user, **overrides):
        data = {
            "name": user.name or "name",
            "email": user.email,
            "is_active": "on",
            "date_joined": user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data.update(overrides)
        return data

    def test_cannot_open_more_privileged_user(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="pw")
        other = User.objects.create_user(email="other@example.com", password="pw")
        other.groups.add(self.admin_group)
        for target in (admin, other):
            for name in ("users:update", "users:admin_change_password"):
                response = self.client.get(reverse(name, kwargs={"pk": target.pk}))
                self.assertEqual(response.status_code, 403, (name, target))

    def test_cannot_edit_or_reactivate_more_privileged_inactive_user(self):
        other = User.objects.create_user(email="other@example.com", password="pw", is_active=False)
        other.groups.add(self.admin_group)
        response = self.client.get(reverse("users:update", kwargs={"pk": other.pk}))
        self.assertEqual(response.status_code, 403)
        self.client.post(reverse("users:update", kwargs={"pk": other.pk}), self.form_data(other))
        other.refresh_from_db()
        self.assertFalse(other.is_active)

    def test_cannot_change_more_privileged_users_password(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        other.groups.add(self.admin_group)
        self.client.post(
            reverse("users:admin_change_password", kwargs={"pk": other.pk}),
            {"password1": "a-new-strong-password-1", "password2": "a-new-strong-password-1"},
        )
        other.refresh_from_db()
        self.assertTrue(other.check_password("pw"))

    def test_cannot_make_self_superuser(self):
        self.client.post(
            reverse("users:update", kwargs={"pk": self.manager.pk}),
            self.form_data(self.manager, is_superuser="on"),
        )
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_superuser)

    def test_cannot_grant_unheld_group_or_permission(self):
        for extra in (
            {"groups": [self.admin_group.pk]},
            {"user_permissions": [perm("delete_rfidinguser").pk]},
        ):
            response = self.client.post(
                reverse("users:update", kwargs={"pk": self.manager.pk}),
                self.form_data(self.manager, **extra),
            )
            self.assertEqual(response.status_code, 200, extra)  # re-rendered with error
        self.assertFalse(self.manager.has_perm("users.delete_rfidinguser"))
        self.assertFalse(self.manager.groups.exists())

    def test_can_edit_equally_privileged_user(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        response = self.client.post(
            reverse("users:update", kwargs={"pk": other.pk}),
            self.form_data(other, name="renamed", user_permissions=[perm("view_rfidinguser").pk]),
        )
        self.assertEqual(response.status_code, 302)
        other.refresh_from_db()
        self.assertEqual(other.name, "renamed")


class GroupManagementEscalationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(email="manager@example.com", password="pw")
        self.manager.user_permissions.add(
            perm("add_group"), perm("change_group"), perm("delete_group")
        )
        self.client.force_login(self.manager)

    def test_cannot_grant_unheld_permission_to_own_group(self):
        group = Group.objects.create(name="mine")
        self.manager.groups.add(group)
        response = self.client.post(
            reverse("users:groups:update", kwargs={"pk": group.pk}),
            {"name": "mine", "permissions": [perm("delete_rfidinguser").pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(group.permissions.exists())

    def test_cannot_create_group_with_unheld_permission(self):
        self.client.post(
            reverse("users:groups:create"),
            {"name": "new", "permissions": [perm("delete_rfidinguser").pk]},
        )
        self.assertFalse(Group.objects.filter(name="new").exists())

    def test_cannot_edit_or_delete_more_privileged_group(self):
        group = Group.objects.create(name="admins")
        group.permissions.add(perm("delete_rfidinguser"))
        for name in ("users:groups:update", "users:groups:delete"):
            response = self.client.get(reverse(name, kwargs={"pk": group.pk}))
            self.assertEqual(response.status_code, 403, name)

    def test_can_grant_held_permission(self):
        group = Group.objects.create(name="mine")
        response = self.client.post(
            reverse("users:groups:update", kwargs={"pk": group.pk}),
            {"name": "mine", "permissions": [perm("change_group").pk]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(group.permissions.filter(codename="change_group").exists())
