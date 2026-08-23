import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from users.models import UserWidget

User = get_user_model()


class LoginRequiredTests(TestCase):
    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 302)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="pass", name="Original"
        )
        self.client.force_login(self.user)

    def test_get_shows_current_user(self):
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"], self.user)

    def test_post_updates_own_profile(self):
        response = self.client.post(
            reverse("users:profile"),
            {
                "name": "Updated",
                "email": "user@example.com",
                "language": "en",
                "date_format": "locale",
                "time_format": "locale",
                "page_length": 50,
                "default_token_filter": "active",
                "default_people_filter": "active",
                "default_machines_filter": "active",
                "theme_mode": "system",
                "light_theme": "default",
                "dark_theme": "default",
                "nav_style": "navbar",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Updated")


class HomeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.client.force_login(self.user)

    def test_hides_widgets_requiring_missing_permission(self):
        UserWidget.objects.create(user=self.user, widget="token_counts", position=0)
        UserWidget.objects.create(
            user=self.user, widget="audit_log_latest", position=1
        )
        response = self.client.get(reverse("home"))
        widgets = list(response.context["widgets"])
        widget_types = [w.widget for w in widgets]
        self.assertIn("token_counts", widget_types)
        self.assertNotIn("audit_log_latest", widget_types)

    def test_shows_permission_gated_widget_once_granted(self):
        UserWidget.objects.create(
            user=self.user, widget="audit_log_latest", position=0
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_token")
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        widget_types = [w.widget for w in response.context["widgets"]]
        self.assertIn("audit_log_latest", widget_types)


class HomeWidgetsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.client.force_login(self.user)

    def test_returns_data_for_widgets(self):
        UserWidget.objects.create(user=self.user, widget="token_counts", position=0)
        response = self.client.get(reverse("users:widgets:home"))
        self.assertEqual(response.status_code, 200)
        widget = response.context["widgets"][0]
        self.assertEqual(widget.data["total_count"], 0)

    def test_filters_by_widget_id(self):
        w1 = UserWidget.objects.create(user=self.user, widget="token_counts", position=0)
        UserWidget.objects.create(user=self.user, widget="people_counts", position=1)
        response = self.client.get(
            reverse("users:widgets:home"), {"widget_id": w1.pk}
        )
        widgets = list(response.context["widgets"])
        self.assertEqual(len(widgets), 1)
        self.assertEqual(widgets[0].pk, w1.pk)


class ChangePasswordViewTests(TestCase):
    def test_own_password_change(self):
        user = User.objects.create_user(email="user@example.com", password="old-pass")
        self.client.force_login(user)
        response = self.client.post(
            reverse("users:change_password"),
            {
                "old_password": "old-pass",
                "new_password1": "a-new-strong-password-1",
                "new_password2": "a-new-strong-password-1",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("a-new-strong-password-1"))


class UserCrudViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.admin)

    def test_list_requires_permission(self):
        self.client.logout()
        plain_user = User.objects.create_user(email="plain@example.com", password="pass")
        self.client.force_login(plain_user)
        response = self.client.get(reverse("users:list"))
        self.assertEqual(response.status_code, 403)

    def test_create_user(self):
        response = self.client.post(
            reverse("users:create"),
            {
                "name": "New User",
                "email": "new@example.com",
                "is_active": "on",
                "date_joined": "2024-01-01 00:00:00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_update_user_shows_can_delete(self):
        target = User.objects.create_user(email="target@example.com", password="pass")
        response = self.client.get(reverse("users:update", kwargs={"pk": target.pk}))
        self.assertTrue(response.context["can_delete"])

    def test_detail_view_shows_permissions(self):
        target = User.objects.create_user(email="target@example.com", password="pass")
        response = self.client.get(reverse("users:detail", kwargs={"pk": target.pk}))
        self.assertTrue(response.context["can_edit"])
        self.assertTrue(response.context["can_delete"])

    def test_delete_user(self):
        target = User.objects.create_user(email="target@example.com", password="pass")
        response = self.client.post(reverse("users:delete", kwargs={"pk": target.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())


class AdminChangePasswordViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.admin)
        self.target = User.objects.create_user(
            email="target@example.com", password="old-password"
        )
        self.url = reverse("users:admin_change_password", kwargs={"pk": self.target.pk})

    def test_context_includes_target_object(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["object"], self.target)

    def test_changes_target_password(self):
        response = self.client.post(
            self.url,
            {
                "password1": "a-new-strong-password-1",
                "password2": "a-new-strong-password-1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password("a-new-strong-password-1"))

    def test_missing_target_is_404(self):
        response = self.client.get(
            reverse("users:admin_change_password", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 404)


class GroupCrudViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.admin)

    def test_create_group(self):
        response = self.client.post(
            reverse("users:groups:create"), {"name": "Instructors"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Group.objects.filter(name="Instructors").exists())

    def test_update_group_shows_can_delete(self):
        group = Group.objects.create(name="Old Name")
        response = self.client.get(reverse("users:groups:update", kwargs={"pk": group.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_delete"])

    def test_create_group_page_renders(self):
        response = self.client.get(reverse("users:groups:create"))
        self.assertEqual(response.status_code, 200)

    def test_delete_group(self):
        group = Group.objects.create(name="Temp")
        response = self.client.post(reverse("users:groups:delete", kwargs={"pk": group.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())


class WidgetViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.client.force_login(self.user)

    def test_create_widget_full_page(self):
        response = self.client.post(
            reverse("users:widgets:create"), {"widget": "token_counts", "width": 4}
        )
        self.assertEqual(response.status_code, 302)
        widget = UserWidget.objects.get(user=self.user)
        self.assertEqual(widget.widget, "token_counts")
        self.assertEqual(widget.position, 0)

    def test_create_widget_partial_returns_rendered_fragment(self):
        response = self.client.post(
            reverse("users:widgets:create"),
            {"widget": "token_counts", "width": 4},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Reswap"], "beforeend")

    def test_update_widget_partial_returns_fragment(self):
        widget = UserWidget.objects.create(user=self.user, widget="token_counts", width=4)
        response = self.client.post(
            reverse("users:widgets:update", kwargs={"pk": widget.pk}),
            {"width": 6},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Retarget"], f"#widget-{widget.pk}")
        widget.refresh_from_db()
        self.assertEqual(widget.width, 6)

    def test_update_widget_scoped_to_own_widgets(self):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        other_widget = UserWidget.objects.create(
            user=other_user, widget="token_counts", width=4
        )
        response = self.client.post(
            reverse("users:widgets:update", kwargs={"pk": other_widget.pk}),
            {"width": 6},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_widget(self):
        widget = UserWidget.objects.create(user=self.user, widget="token_counts")
        response = self.client.post(
            reverse("users:widgets:delete", kwargs={"pk": widget.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserWidget.objects.filter(pk=widget.pk).exists())

    def test_delete_widget_scoped_to_own_widgets(self):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        other_widget = UserWidget.objects.create(user=other_user, widget="token_counts")
        response = self.client.post(
            reverse("users:widgets:delete", kwargs={"pk": other_widget.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(UserWidget.objects.filter(pk=other_widget.pk).exists())

    def test_reorder_widgets(self):
        w1 = UserWidget.objects.create(user=self.user, widget="token_counts", position=0)
        w2 = UserWidget.objects.create(user=self.user, widget="people_counts", position=1)
        response = self.client.post(
            reverse("users:widgets:reorder"),
            {"order": json.dumps([w2.pk, w1.pk])},
        )
        self.assertEqual(response.status_code, 204)
        w1.refresh_from_db()
        w2.refresh_from_db()
        self.assertEqual(w2.position, 0)
        self.assertEqual(w1.position, 1)

    def test_reorder_ignores_unknown_widget_ids(self):
        w1 = UserWidget.objects.create(user=self.user, widget="token_counts", position=0)
        response = self.client.post(
            reverse("users:widgets:reorder"),
            {"order": json.dumps([999999, w1.pk])},
        )
        self.assertEqual(response.status_code, 204)

    def test_reorder_invalid_json_is_bad_request(self):
        response = self.client.post(
            reverse("users:widgets:reorder"), {"order": "not-json"}
        )
        self.assertEqual(response.status_code, 400)
