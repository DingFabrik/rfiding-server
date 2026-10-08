from django.test import SimpleTestCase, TestCase, override_settings
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from machines.models import Machine
from people import checks

SMTP = "django.core.mail.backends.smtp.EmailBackend"
TEMPLATES = {"qualification_expiration": {"email": {"subject": "s", "body": "b"}}}


def ids(messages):
    return [message.id for message in messages]


@override_settings(
    PERSON_ENABLE_EMAIL=True,
    EMAIL_BACKEND=SMTP,
    DEFAULT_FROM_EMAIL="rfiding@example.com",
)
class EmailNotificationCheckTests(SimpleTestCase):
    def test_configured_email_passes(self):
        self.assertEqual(checks.check_email_notifications(None), [])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_non_delivering_backend(self):
        self.assertEqual(ids(checks.check_email_notifications(None)), ["people.W001"])

    @override_settings(DEFAULT_FROM_EMAIL="webmaster@localhost")
    def test_placeholder_sender(self):
        self.assertEqual(ids(checks.check_email_notifications(None)), ["people.W002"])

    @override_settings(PERSON_ENABLE_EMAIL=False, DEFAULT_FROM_EMAIL="webmaster@localhost")
    def test_disabled_email_is_not_checked(self):
        self.assertEqual(checks.check_email_notifications(None), [])


@override_settings(PERSON_ENABLE_SLACK_EMAIL=True, PERSON_SLACK_TOKEN="xoxb-token")
class SlackNotificationCheckTests(SimpleTestCase):
    def test_token_set(self):
        self.assertEqual(checks.check_slack_notifications(None), [])

    @override_settings(PERSON_SLACK_TOKEN=None)
    def test_missing_token(self):
        self.assertEqual(ids(checks.check_slack_notifications(None)), ["people.W003"])

    @override_settings(PERSON_ENABLE_SLACK_EMAIL=False, PERSON_SLACK_TOKEN=None)
    def test_disabled_slack_is_not_checked(self):
        self.assertEqual(checks.check_slack_notifications(None), [])


@override_settings(PERSON_ENABLE_EMAIL=True)
class NotificationTemplateCheckTests(SimpleTestCase):
    @override_settings(PERSON_NOTIFICATION_TEMPLATES=TEMPLATES)
    def test_expiration_template_configured(self):
        self.assertEqual(checks.check_notification_templates(None), [])

    @override_settings(PERSON_NOTIFICATION_TEMPLATES={"default": TEMPLATES["qualification_expiration"]})
    def test_default_template_configured(self):
        self.assertEqual(checks.check_notification_templates(None), [])

    @override_settings(PERSON_NOTIFICATION_TEMPLATES={})
    def test_missing_template(self):
        self.assertEqual(ids(checks.check_notification_templates(None)), ["people.W004"])


class ExpiryTasksScheduledCheckTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="lathe", name="Lathe"
        )
        self.schedule = IntervalSchedule.objects.create(every=1, period=IntervalSchedule.DAYS)

    def run_check(self):
        return ids(checks.check_expiry_tasks_scheduled(None, databases=["default"]))

    def schedule_task(self, task, enabled=True):
        PeriodicTask.objects.create(
            name=task, task=task, interval=self.schedule, enabled=enabled
        )

    def test_no_expiry_configured(self):
        self.assertEqual(self.run_check(), [])

    def test_unscheduled_tasks(self):
        Machine.objects.filter(pk=self.machine.pk).update(qualification_expiry_unused_days=90)
        self.assertEqual(self.run_check(), ["people.W005", "people.W006"])

    def test_scheduled_tasks(self):
        Machine.objects.filter(pk=self.machine.pk).update(qualification_expiry_used_days=365)
        self.schedule_task(checks.EXPIRE_TASK)
        self.schedule_task(checks.NOTIFY_TASK)
        self.assertEqual(self.run_check(), [])

    def test_disabled_task_counts_as_unscheduled(self):
        Machine.objects.filter(pk=self.machine.pk).update(qualification_expiry_used_days=365)
        self.schedule_task(checks.EXPIRE_TASK, enabled=False)
        self.schedule_task(checks.NOTIFY_TASK)
        self.assertEqual(self.run_check(), ["people.W005"])

    def test_skipped_without_database(self):
        Machine.objects.filter(pk=self.machine.pk).update(qualification_expiry_unused_days=90)
        self.assertEqual(checks.check_expiry_tasks_scheduled(None), [])

    def test_tasks_exist_under_the_checked_names(self):
        from rfiding.celery import app

        app.loader.import_default_modules()
        self.assertIn(checks.EXPIRE_TASK, app.tasks)
        self.assertIn(checks.NOTIFY_TASK, app.tasks)
