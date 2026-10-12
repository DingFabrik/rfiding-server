import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from machines.models import Machine
from people.models import Person, Qualification
from people.self_service import SESSION_KEY


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SelfServiceLoginTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Lena Vogt", email="lena@example.com")

    def request_code(self, email="lena@example.com"):
        return self.client.post(reverse("people:me-login"), {"email": email})

    def sent_code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def test_me_redirects_to_login_when_signed_out(self):
        response = self.client.get(reverse("people:me"))
        self.assertRedirects(response, reverse("people:me-login"))

    def test_request_sends_code_and_link(self):
        response = self.request_code("LENA@example.com")
        self.assertRedirects(response, reverse("people:me-verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["lena@example.com"])
        self.person.refresh_from_db()
        self.assertIn(self.person.get_detail_url(), mail.outbox[0].body)
        self.assertIn(self.sent_code(), mail.outbox[0].subject)

    def test_unknown_email_looks_the_same_but_sends_nothing(self):
        response = self.request_code("nobody@example.com")
        self.assertRedirects(response, reverse("people:me-verify"))
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_person_gets_no_code(self):
        self.person.is_active = False
        self.person.save()
        self.request_code()
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_is_throttled(self):
        self.request_code()
        self.request_code()
        self.assertEqual(len(mail.outbox), 1)

    def test_correct_code_signs_in(self):
        self.request_code()
        response = self.client.post(
            reverse("people:me-verify"), {"code": self.sent_code()}
        )
        self.assertRedirects(response, reverse("people:me"))
        self.assertEqual(self.client.session[SESSION_KEY]["id"], self.person.pk)

    def test_code_is_single_use(self):
        self.request_code()
        code = self.sent_code()
        self.client.post(reverse("people:me-verify"), {"code": code})
        self.assertTrue(self.client.session.get(SESSION_KEY))
        self.person.refresh_from_db()
        self.assertFalse(self.person.check_login_code(code))

    def test_wrong_code_is_rejected(self):
        self.request_code()
        wrong = "000000" if self.sent_code() != "000000" else "111111"
        response = self.client.post(reverse("people:me-verify"), {"code": wrong})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    @patch("people.models.PERSON_LOGIN_CODE_MAX_ATTEMPTS", 3)
    def test_too_many_attempts_invalidate_code(self):
        self.request_code()
        code = self.sent_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(3):
            self.client.post(reverse("people:me-verify"), {"code": wrong})
        self.client.post(reverse("people:me-verify"), {"code": code})
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    def test_expired_code_is_rejected(self):
        self.request_code()
        code = self.sent_code()
        Person.objects.filter(pk=self.person.pk).update(
            detail_key_expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.client.post(reverse("people:me-verify"), {"code": code})
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    @patch("people.models.PERSON_LOGIN_CODE_VALID_MINUTES", 5)
    def test_code_expiry_uses_configured_duration(self):
        self.person.generate_login_code()
        self.assertAlmostEqual(
            self.person.detail_key_expires_at,
            timezone.now() + timedelta(minutes=5),
            delta=timedelta(seconds=5),
        )

    def test_logout_ends_session_and_link(self):
        self.request_code()
        self.client.post(reverse("people:me-verify"), {"code": self.sent_code()})
        self.person.refresh_from_db()
        link = self.person.get_detail_url()
        response = self.client.post(reverse("people:me-logout"))
        self.assertRedirects(response, reverse("people:me-login"))
        self.assertIsNone(self.client.session.get(SESSION_KEY))
        self.assertEqual(self.client.get(link).status_code, 403)

    def test_session_expires(self):
        self.request_code()
        self.client.post(reverse("people:me-verify"), {"code": self.sent_code()})
        session = self.client.session
        session[SESSION_KEY]["expires"] = timezone.now().timestamp() - 1
        session.save()
        response = self.client.get(reverse("people:me"))
        self.assertRedirects(response, reverse("people:me-login"))


class MyQualificationsPageTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Lena Vogt", email="lena@example.com")
        self.instructor = Person.objects.create(name="Tobias Hahn", email="t@example.com")
        self.other = Person.objects.create(name="Someone Else", email="s@example.com")
        session = self.client.session
        session[SESSION_KEY] = {
            "id": self.person.pk,
            "expires": (timezone.now() + timedelta(hours=1)).timestamp(),
        }
        session.save()

    def qualify(self, person, name, **kwargs):
        machine = Machine.objects.create(name=name)
        return Qualification.objects.create(person=person, machine=machine, **kwargs)

    def test_shows_only_own_qualifications_sorted_by_attention(self):
        now = timezone.now()
        self.qualify(self.person, "Soldering station", instructed_by=self.instructor)
        self.qualify(self.person, "CNC router", expired=now - timedelta(days=3))
        self.qualify(self.person, "Table saw", expires_at=now + timedelta(days=22))
        self.qualify(self.other, "Not mine")

        response = self.client.get(reverse("people:me"))
        self.assertContains(response, "Lena Vogt")
        self.assertContains(response, "Tobias Hahn")
        self.assertNotContains(response, "Not mine")
        names = [row.machine.name for row in response.context["rows"]]
        self.assertEqual(names, ["Table saw", "CNC router", "Soldering station"])
        statuses = [row.status for row in response.context["rows"]]
        self.assertEqual(statuses, ["expiring", "expired", "valid"])

    def test_links_to_public_machine_pages(self):
        qualification = self.qualify(self.person, "Table saw")
        response = self.client.get(reverse("people:me"))
        self.assertContains(
            response,
            reverse("machines:detail", args=[qualification.machine.pk]) + "?public=true",
        )


class StaffLoginPageTests(TestCase):
    def test_links_to_self_service_login(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, reverse("people:me-login"))
