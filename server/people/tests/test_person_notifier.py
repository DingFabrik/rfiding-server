from django.test import TestCase
from machines.models import Machine
from people.models import Person, Qualification


class PersonNotifierTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.person_with_email = Person.objects.create(name="test", email="test@example.com")
        self.person_without_email = Person.objects.create(name="test2", email=None)

    def test_email_notifier_can_notify(self):
        from people.notifiers import EmailNotifier

        notifier = EmailNotifier()
        self.assertTrue(notifier.can_notify(self.person_with_email))
        self.assertFalse(notifier.can_notify(self.person_without_email))

    def test_email_notifier_uses_fallback_template(self):
        from django.core import mail

        from people.notifiers import EmailNotifier

        notifier = EmailNotifier()
        sent = notifier.send(self.person_with_email, "some_unconfigured_type")
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.person_with_email.name, mail.outbox[0].body)

    def test_slack_notifier_cannot_notify_without_contact_info(self):
        from people.notifiers import SlackNotifier

        notifier = SlackNotifier()
        self.assertFalse(notifier.can_notify(self.person_with_email))

    def test_notify_person_returns_channels_actually_sent(self):
        from people.notifications import notify_person

        sent_via = notify_person(self.person_with_email, "some_unconfigured_type")
        self.assertEqual(sent_via, ["email"])

    def test_notify_person_uses_configured_template(self):
        from django.core import mail
        from django.test import override_settings

        from people.notifiers import EmailNotifier

        templates = {
            "qualification_expiration": {
                "email": {
                    "subject": "Bye {{ machine_name }}",
                    "body": "{{ person_name }} loses access to {{ machine_name }} on {{ expires_at }}",
                },
            },
        }
        with override_settings(PERSON_NOTIFICATION_TEMPLATES=templates):
            notifier = EmailNotifier()
            notifier.send(
                self.person_with_email,
                "qualification_expiration",
                {"machine_name": "Laser Cutter", "expires_at": "2026-01-01"},
            )
        self.assertEqual(mail.outbox[0].subject, "Bye Laser Cutter")
        self.assertIn("Laser Cutter", mail.outbox[0].body)

    def test_send_qualification_expiration_notification(self):
        from django.core import mail

        qualification = Qualification.objects.create(
            machine=self.machine, person=self.person_with_email
        )
        from people.notifications import send_qualification_expiration_notification

        sent_via = send_qualification_expiration_notification(qualification)
        self.assertEqual(sent_via, ["email"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.machine.name, mail.outbox[0].body)
