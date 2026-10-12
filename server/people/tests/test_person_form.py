import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from people.forms import PersonForm


class PersonFormAutocompleteTests(TestCase):
    """Members' details must not be saved to the browser's autofill."""

    def test_identifying_fields_disable_autocomplete(self):
        form = PersonForm()
        for name in PersonForm.no_autocomplete_fields:
            if name in form.fields:
                self.assertEqual(form.fields[name].widget.attrs.get("autocomplete"), "off")

    def test_rendered_create_form_disables_autocomplete(self):
        user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("people:create"))
        content = response.content.decode()
        for name in ("name", "email"):
            tag = re.search(rf'<input[^>]*name="{name}"[^>]*>', content).group(0)
            self.assertIn('autocomplete="off"', tag)
