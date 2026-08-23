from django.test import TestCase

from users.models import RFIDingUser, UserWidget

User = RFIDingUser


class UserManagerTests(TestCase):
    def test_create_user_sets_password_and_defaults(self):
        user = User.objects.create_user(email="user@example.com", password="pw")
        self.assertTrue(user.check_password("pw"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pw")

    def test_create_user_normalizes_email_domain(self):
        user = User.objects.create_user(email="user@EXAMPLE.COM", password="pw")
        self.assertEqual(user.email, "user@example.com")

    def test_create_superuser_sets_staff_and_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pw")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="pw", is_staff=False
            )

    def test_create_superuser_rejects_is_superuser_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="pw", is_superuser=False
            )


class RFIDingUserTests(TestCase):
    def test_str_returns_name(self):
        user = User.objects.create_user(
            email="user@example.com", password="pw", name="Alice"
        )
        self.assertEqual(str(user), "Alice")


class UserWidgetPropertiesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pw")

    def make_widget(self, widget):
        return UserWidget(user=self.user, widget=widget)

    def test_token_counts_and_people_counts_share_template(self):
        self.assertEqual(self.make_widget("token_counts").template, "widgets/count.html")
        self.assertEqual(self.make_widget("people_counts").template, "widgets/count.html")

    def test_each_widget_has_a_template_title_and_icon(self):
        for widget_key, _label in (
            ("token_counts", None),
            ("people_counts", None),
            ("machine_counts", None),
            ("access_log_latest", None),
            ("access_log_chart", None),
            ("audit_log_latest", None),
            ("pending_registration_requests", None),
            ("space_status", None),
            ("machines_maintenance", None),
        ):
            widget = self.make_widget(widget_key)
            with self.subTest(widget=widget_key):
                self.assertIsNotNone(widget.template)
                self.assertIsNotNone(widget.title)
                self.assertIsNotNone(widget.icon)

    def test_unknown_widget_type_returns_none_for_all_properties(self):
        widget = self.make_widget("does-not-exist")
        self.assertIsNone(widget.template)
        self.assertIsNone(widget.title)
        self.assertIsNone(widget.icon)

    def test_specific_titles_and_icons(self):
        widget = self.make_widget("machine_counts")
        self.assertEqual(widget.title, "Machines")
        self.assertEqual(widget.icon, "hard-drive")
        self.assertEqual(widget.template, "widgets/machine_count.html")
