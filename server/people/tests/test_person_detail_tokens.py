from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from people.models import Person
from tokens.models import Token, TokenType


class PersonDetailTokensTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(name="test", email="test@example.com")

    def get_detail(self):
        return self.client.get(reverse("people:detail", kwargs={"pk": self.person.pk}))

    def test_token_card_shows_formatted_label(self):
        token_type = TokenType.objects.create(
            name="Key fob", label_prefix="K", label_id_padding=3
        )
        Token.objects.create(
            serial="aabbcc", person=self.person, type=token_type, label_id=12
        )
        self.assertContains(self.get_detail(), "Token #K012")

    def test_token_card_without_label_shows_purpose(self):
        Token.objects.create(serial="aabbcc", person=self.person, purpose="Spare card")
        response = self.get_detail()
        self.assertContains(response, "Spare card")
        self.assertNotContains(response, "Token #")
