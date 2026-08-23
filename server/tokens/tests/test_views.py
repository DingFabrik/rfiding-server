from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from machines.models import Machine
from people.models import Person
from tokens.models import BlacklistedToken, Token, TokenType, UnknownToken

User = get_user_model()


class TokenViewsTestCase(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.superuser)
        self.person = Person.objects.create(name="Alice", email="alice@example.com")
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )


class TokenListViewTests(TokenViewsTestCase):
    url = reverse("tokens:list")

    def setUp(self):
        super().setUp()
        self.active_token = Token.objects.create(
            serial="1", person=self.person, purpose="active"
        )
        self.inactive_token = Token.objects.create(
            serial="2", person=self.person, purpose="inactive", is_active=False
        )
        self.archived_token = Token.objects.create(
            serial="3", person=self.person, purpose="archived", is_active=False,
        )
        self.archived_token.archived = self.archived_token.created
        self.archived_token.save()

    def test_default_filter_shows_active_tokens(self):
        response = self.client.get(self.url)
        tokens = list(response.context["tokens"])
        self.assertIn(self.active_token, tokens)
        self.assertNotIn(self.inactive_token, tokens)
        self.assertNotIn(self.archived_token, tokens)

    def test_all_filter_excludes_only_archived(self):
        response = self.client.get(self.url, {"filter_status": "all"})
        tokens = list(response.context["tokens"])
        self.assertIn(self.active_token, tokens)
        self.assertIn(self.inactive_token, tokens)
        self.assertNotIn(self.archived_token, tokens)

    def test_inactive_filter(self):
        response = self.client.get(self.url, {"filter_status": "inactive"})
        tokens = list(response.context["tokens"])
        self.assertEqual(tokens, [self.inactive_token])

    def test_archived_filter(self):
        response = self.client.get(self.url, {"filter_status": "archived"})
        tokens = list(response.context["tokens"])
        self.assertEqual(tokens, [self.archived_token])

    def test_type_filter(self):
        token_type = TokenType.objects.create(name="RFID")
        typed_token = Token.objects.create(
            serial="4", person=self.person, purpose="typed", type=token_type
        )
        response = self.client.get(
            self.url, {"filter_status": "all", "filter_type": str(token_type.pk)}
        )
        tokens = list(response.context["tokens"])
        self.assertEqual(tokens, [typed_token])

    def test_type_filter_choices_populated_when_types_exist(self):
        TokenType.objects.create(name="RFID")
        response = self.client.get(self.url)
        options = response.context["filter_choices"]["type"]["options"]
        self.assertEqual(options[0], ("all", "All"))
        self.assertEqual(len(options), 2)


class UnknownTokenListViewTests(TokenViewsTestCase):
    url = reverse("tokens:unknown")

    def test_context_includes_create_permissions(self):
        response = self.client.get(self.url)
        self.assertTrue(response.context["can_create_token"])
        self.assertTrue(response.context["can_create_blacklistedtoken"])


class ClearUnknownTokensViewTests(TokenViewsTestCase):
    url = reverse("tokens:clear-unknown")

    def test_clears_all_unknown_tokens(self):
        UnknownToken.objects.create(serial="123", machine=self.machine)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("tokens:unknown"))
        self.assertFalse(UnknownToken.objects.exists())


class AssignTokenViewTests(TokenViewsTestCase):
    def test_prefills_serial_and_clears_unknown_token(self):
        UnknownToken.objects.create(serial="999", machine=self.machine)
        url = reverse("tokens:assign", kwargs={"serial": "999"})

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertTrue(get_response.context["prefilled_serial"])
        self.assertEqual(get_response.context["form"].initial["serial"], "999")

        token_type = TokenType.objects.create(name="RFID")
        post_response = self.client.post(
            url,
            {
                "serial": "999",
                "person": self.person.pk,
                "purpose": "test",
                "is_active": "on",
                "type": token_type.pk,
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(Token.objects.filter(serial="999").exists())
        self.assertFalse(UnknownToken.objects.exists())


class TokenDetailViewTests(TokenViewsTestCase):
    def test_shows_edit_and_delete_permissions(self):
        token = Token.objects.create(serial="1", person=self.person, purpose="test")
        response = self.client.get(reverse("tokens:detail", kwargs={"pk": token.pk}))
        self.assertTrue(response.context["can_edit"])
        self.assertTrue(response.context["can_delete"])


class TokenUpdateViewTests(TokenViewsTestCase):
    def test_updates_token(self):
        # `purpose` isn't part of TokenForm's editable fields; `notes` is.
        token_type = TokenType.objects.create(name="RFID")
        token = Token.objects.create(serial="1", person=self.person, purpose="test")
        response = self.client.post(
            reverse("tokens:update", kwargs={"pk": token.pk}),
            {
                "serial": "1",
                "person": self.person.pk,
                "notes": "updated notes",
                "is_active": "on",
                "type": token_type.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        token.refresh_from_db()
        self.assertEqual(token.notes, "updated notes")


class TokenArchiveViewTests(TokenViewsTestCase):
    def test_post_archives_token_instead_of_deleting(self):
        token = Token.objects.create(serial="1", person=self.person, purpose="test")
        response = self.client.post(reverse("tokens:delete", kwargs={"pk": token.pk}))
        self.assertRedirects(response, reverse("tokens:list"))
        token.refresh_from_db()
        self.assertFalse(token.is_active)
        self.assertIsNotNone(token.archived)
        self.assertTrue(Token.objects.filter(pk=token.pk).exists())


class TokenToggleActiveViewTests(TokenViewsTestCase):
    def test_toggles_active_state(self):
        token = Token.objects.create(serial="1", person=self.person, purpose="test")
        response = self.client.post(
            reverse("tokens:toggle-active", kwargs={"pk": token.pk})
        )
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertFalse(token.is_active)


class PersonForTokenPopoverViewTests(TokenViewsTestCase):
    def test_returns_person_for_token(self):
        token = Token.objects.create(serial="1", person=self.person, purpose="test")
        response = self.client.get(
            reverse("tokens:person-for-token-popover"), {"token_pk": token.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"], self.person)


class BlacklistTokenViewTests(TokenViewsTestCase):
    def test_blacklists_and_clears_unknown_token(self):
        UnknownToken.objects.create(serial="777", machine=self.machine)
        response = self.client.get(
            reverse("tokens:blacklist-token", kwargs={"serial": "777"})
        )
        self.assertRedirects(response, reverse("tokens:blacklisted"))
        self.assertTrue(BlacklistedToken.objects.filter(serial="777").exists())
        self.assertFalse(UnknownToken.objects.filter(serial="777").exists())


class BlacklistedTokenListViewTests(TokenViewsTestCase):
    def test_lists_blacklisted_tokens(self):
        BlacklistedToken.objects.create(serial="1")
        response = self.client.get(reverse("tokens:blacklisted"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["tokens"]), 1)


class BlacklistedTokenDeleteViewTests(TokenViewsTestCase):
    def test_deletes_blacklisted_token(self):
        blacklisted = BlacklistedToken.objects.create(serial="1")
        response = self.client.post(
            reverse("tokens:delete-blacklisted", kwargs={"pk": blacklisted.pk})
        )
        self.assertRedirects(response, reverse("tokens:blacklisted"))
        self.assertFalse(BlacklistedToken.objects.filter(pk=blacklisted.pk).exists())


class NextFreeTokenLabelViewTests(TokenViewsTestCase):
    url = reverse("tokens:next-label-id")

    def test_no_tokens_starts_at_one(self):
        response = self.client.get(self.url)
        self.assertIn("1", response.content.decode())

    def test_increments_from_highest_untyped_label(self):
        Token.objects.create(
            serial="1", person=self.person, purpose="test", label_id=5
        )
        response = self.client.get(self.url)
        self.assertIn("6", response.content.decode())

    def test_type_specific_labels_use_type_format(self):
        token_type = TokenType.objects.create(
            name="RFID", label_prefix="RF", label_id_padding=3
        )
        Token.objects.create(
            serial="1", person=self.person, purpose="test", label_id=4, type=token_type
        )
        response = self.client.get(self.url, {"type": str(token_type.pk)})
        self.assertIn("RF005", response.content.decode())

    def test_type_specific_labels_ignore_untyped_tokens(self):
        token_type = TokenType.objects.create(name="RFID")
        Token.objects.create(
            serial="1", person=self.person, purpose="test", label_id=99
        )
        response = self.client.get(self.url, {"type": str(token_type.pk)})
        self.assertIn("1", response.content.decode())
        self.assertNotIn("100", response.content.decode())


class TokenTypeViewsTests(TokenViewsTestCase):
    def test_list_paginates_by_user_page_length(self):
        response = self.client.get(reverse("tokens:types:list"))
        self.assertEqual(response.status_code, 200)

    def test_create_page_renders(self):
        # Regression: base_form.html's breadcrumb links to a "<namespace>:detail"
        # URL that doesn't exist for token types; tokentype_form.html overrides it.
        response = self.client.get(reverse("tokens:types:create"))
        self.assertEqual(response.status_code, 200)

    def test_update_page_renders(self):
        token_type = TokenType.objects.create(name="RFID")
        response = self.client.get(
            reverse("tokens:types:update", kwargs={"pk": token_type.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_create_token_type(self):
        response = self.client.post(
            reverse("tokens:types:create"),
            {"name": "RFID", "description": "", "label_prefix": "", "label_id_padding": 0},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TokenType.objects.filter(name="RFID").exists())

    def test_update_token_type(self):
        token_type = TokenType.objects.create(name="RFID")
        response = self.client.post(
            reverse("tokens:types:update", kwargs={"pk": token_type.pk}),
            {"name": "NFC", "description": "", "label_prefix": "", "label_id_padding": 0},
        )
        self.assertEqual(response.status_code, 302)
        token_type.refresh_from_db()
        self.assertEqual(token_type.name, "NFC")

    def test_delete_token_type(self):
        token_type = TokenType.objects.create(name="RFID")
        response = self.client.post(
            reverse("tokens:types:delete", kwargs={"pk": token_type.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TokenType.objects.filter(pk=token_type.pk).exists())


class TokenPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.client.force_login(self.user)

    def test_list_requires_permission(self):
        response = self.client.get(reverse("tokens:list"))
        self.assertEqual(response.status_code, 403)

    def test_user_with_permission_can_view_list(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_token")
        )
        response = self.client.get(reverse("tokens:list"))
        self.assertEqual(response.status_code, 200)
