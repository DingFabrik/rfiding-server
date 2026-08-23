from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from people.models import Person
from .models import Comment


class CommentCreateViewHtmxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(name="test", email="test@example.com")
        self.url = reverse("people:add-comment", kwargs={"pk": self.person.pk})

    def test_htmx_valid_submission_returns_tab_pane_fragment(self):
        response = self.client.post(
            self.url, {"text": "hello"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="comments-tab-pane"', content)
        self.assertNotIn("<!DOCTYPE", content)
        self.assertIn("hello", content)
        self.assertEqual(Comment.objects.count(), 1)

    def test_htmx_invalid_submission_returns_tab_pane_fragment_with_errors(self):
        response = self.client.post(self.url, {"text": ""}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="comments-tab-pane"', content)
        self.assertNotIn("<!DOCTYPE", content)
        self.assertEqual(Comment.objects.count(), 0)

    def test_non_htmx_valid_submission_redirects(self):
        response = self.client.post(self.url, {"text": "hello"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
