from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from access_log.models import LOG_TYPE_BOOTED, LOG_TYPE_DISABLED, LOG_TYPE_ENABLED, AccessLog
from access_log.tasks import save_access_log
from machines.models import Machine
from people.models import Person
from tokens.models import Token


class DisabledLogTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m", log_disabled=True
        )
        person = Person.objects.create(name="Ada", email="ada@example.com")
        self.token = Token.objects.create(serial="ada", person=person)
        self.other = Token.objects.create(serial="other", person=person)
        self.now = timezone.now()

    def log(self, log_type, token, minutes_ago):
        AccessLog.objects.create(
            machine=self.machine,
            token=token,
            type=log_type,
            timestamp=self.now - timedelta(minutes=minutes_ago),
        )

    def enabled(self, token, minutes_ago):
        self.log(LOG_TYPE_ENABLED, token, minutes_ago)

    def disable(self, token_id=None):
        save_access_log(self.machine.pk, token_id, LOG_TYPE_DISABLED, timestamp=self.now)
        return AccessLog.objects.filter(type=LOG_TYPE_DISABLED).latest("timestamp")

    def test_disable_with_token_ends_that_tokens_enable(self):
        self.enabled(self.token, 30)
        self.enabled(self.other, 10)
        log = self.disable(self.token.pk)
        self.assertEqual(log.token, self.token)
        self.assertEqual(log.enabled_duration, timedelta(minutes=30))

    def test_disable_without_token_is_attributed_to_the_last_enable(self):
        self.enabled(self.other, 30)
        self.enabled(self.token, 10)
        log = self.disable()
        self.assertEqual(log.token, self.token)
        self.assertEqual(log.enabled_duration, timedelta(minutes=10))

    def test_enable_that_was_already_disabled_is_not_attributed_again(self):
        self.enabled(self.token, 10)
        self.log(LOG_TYPE_DISABLED, self.token, 5)
        log = self.disable()
        self.assertIsNone(log.token)
        self.assertIsNone(log.enabled_duration)

    def test_stale_enable_is_not_attributed(self):
        self.enabled(self.token, 60 * 24)
        log = self.disable()
        self.assertIsNone(log.token)

    def test_nothing_is_logged_unless_the_machine_logs_disables(self):
        self.machine.log_disabled = False
        self.machine.save()
        save_access_log(self.machine.pk, None, LOG_TYPE_DISABLED, timestamp=self.now)
        self.assertFalse(AccessLog.objects.filter(type=LOG_TYPE_DISABLED).exists())


class TimestampTests(TestCase):
    def test_log_keeps_the_time_of_the_event(self):
        machine = Machine.objects.create(mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m")
        # E.g. a Celery task that ran late because it was retried.
        event_time = timezone.now() - timedelta(minutes=10)
        save_access_log(machine.pk, None, LOG_TYPE_BOOTED, timestamp=event_time)
        self.assertEqual(AccessLog.objects.get().timestamp, event_time)

    def test_timestamp_defaults_to_now(self):
        machine = Machine.objects.create(mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m")
        before = timezone.now()
        log = AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
        self.assertGreaterEqual(log.timestamp, before)
