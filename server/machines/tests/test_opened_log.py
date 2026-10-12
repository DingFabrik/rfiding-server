"""Locks and compartments log a successful access as "opened" instead of "enabled"."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from access_log.models import (
    AccessLog,
    LOG_TYPE_DISABLED,
    LOG_TYPE_ENABLED,
    LOG_TYPE_OPENED,
    LOG_TYPE_UNSUCCESSFUL,
)
from access_log.tasks import save_access_log
from api.tests import authenticate
from machines.api.common import AccessDenied, check_access
from machines.models import Machine
from people.models import Person, Qualification
from tokens.models import Token


class AccessLogTypeTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(name="Ada", email="ada@example.com")
        self.token = Token.objects.create(serial="ada", person=self.person)

    def machine(self, type, **kwargs):
        return Machine.objects.create(name=type, type=type, **kwargs)

    def check(self, machine, compartment_id=None, qualify=True):
        checked = machine
        if compartment_id is not None:
            checked = machine.children.get(compartment_id=compartment_id)
        if qualify:
            Qualification.objects.create(
                machine=checked, person=self.person, permission_level="always"
            )
        # The qualified path logs once the transaction commits.
        with self.captureOnCommitCallbacks(execute=True):
            return check_access(machine, self.token.serial, compartment_id)

    def logged_types(self, machine):
        return list(AccessLog.objects.filter(machine=machine).values_list("type", flat=True))

    def test_primary_machine_logs_enabled(self):
        machine = self.machine(Machine.MachineType.PRIMARY)
        self.check(machine)
        self.assertEqual(self.logged_types(machine), [LOG_TYPE_ENABLED])

    def test_secondary_machine_logs_enabled(self):
        machine = self.machine(Machine.MachineType.SECONDARY)
        self.check(machine)
        self.assertEqual(self.logged_types(machine), [LOG_TYPE_ENABLED])

    def test_lock_logs_opened(self):
        lock = self.machine(Machine.MachineType.LOCK)
        self.check(lock)
        self.assertEqual(self.logged_types(lock), [LOG_TYPE_OPENED])

    def test_lock_without_qualification_logs_opened(self):
        lock = self.machine(
            Machine.MachineType.LOCK, needs_qualification=False, permission_level="always"
        )
        self.check(lock, qualify=False)
        self.assertEqual(self.logged_types(lock), [LOG_TYPE_OPENED])

    def test_compartment_logs_opened_on_the_compartment(self):
        locker = self.machine(Machine.MachineType.LOCK_GROUP)
        compartment = Machine.objects.create(
            name="Compartment 1", type=Machine.MachineType.COMPARTMENT,
            parent=locker, compartment_id="1",
        )
        self.check(locker, compartment_id="1")
        self.assertEqual(self.logged_types(compartment), [LOG_TYPE_OPENED])
        self.assertEqual(self.logged_types(locker), [])

    def test_maintainer_bypass_on_lock_logs_opened(self):
        lock = self.machine(Machine.MachineType.LOCK, state=Machine.MachineStatus.MAINTENANCE)
        self.person.is_system_maintainer = True
        self.person.save()
        self.check(lock, qualify=False)
        self.assertEqual(self.logged_types(lock), [LOG_TYPE_OPENED])

    def test_lock_respects_log_enabled_setting(self):
        lock = self.machine(Machine.MachineType.LOCK, log_enabled=False)
        self.check(lock)
        self.assertEqual(self.logged_types(lock), [])

    def test_denied_lock_access_is_not_logged_as_opened(self):
        lock = self.machine(Machine.MachineType.LOCK)
        with self.assertRaises(AccessDenied):
            self.check(lock, qualify=False)
        self.assertNotIn(LOG_TYPE_OPENED, self.logged_types(lock))


class SaveOpenedLogTests(TestCase):
    def setUp(self):
        self.lock = Machine.objects.create(
            name="Lock", type=Machine.MachineType.LOCK, log_disabled=True
        )
        person = Person.objects.create(name="Ada", email="ada@example.com")
        self.token = Token.objects.create(serial="ada", person=person)
        self.now = timezone.now()

    def test_opened_is_saved(self):
        save_access_log(self.lock.pk, self.token.pk, LOG_TYPE_OPENED, timestamp=self.now)
        log = AccessLog.objects.get()
        self.assertEqual(log.type, LOG_TYPE_OPENED)
        self.assertEqual(log.token, self.token)

    def test_opened_is_skipped_when_machine_does_not_log_enables(self):
        self.lock.log_enabled = False
        self.lock.save()
        save_access_log(self.lock.pk, self.token.pk, LOG_TYPE_OPENED, timestamp=self.now)
        self.assertFalse(AccessLog.objects.exists())

    def test_duplicate_opened_is_not_saved_twice(self):
        save_access_log(self.lock.pk, self.token.pk, LOG_TYPE_OPENED, timestamp=self.now)
        save_access_log(self.lock.pk, self.token.pk, LOG_TYPE_OPENED, timestamp=self.now)
        self.assertEqual(AccessLog.objects.count(), 1)

    def test_disable_is_attributed_to_whoever_opened_the_lock(self):
        AccessLog.objects.create(
            machine=self.lock, token=self.token, type=LOG_TYPE_OPENED,
            timestamp=self.now - timedelta(minutes=20),
        )
        save_access_log(self.lock.pk, None, LOG_TYPE_DISABLED, timestamp=self.now)
        disabled = AccessLog.objects.get(type=LOG_TYPE_DISABLED)
        self.assertEqual(disabled.token, self.token)
        self.assertEqual(disabled.enabled_duration, timedelta(minutes=20))


class OpenedCountsAsUseTests(TestCase):
    """Wherever a successful access counts as use, "opened" counts like "enabled"."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.lock = Machine.objects.create(
            name="Lock", type=Machine.MachineType.LOCK,
            mac_address="aa:bb:cc:dd:ee:01", hostname="lock",
        )

    def test_machine_list_last_used(self):
        log = AccessLog.objects.create(machine=self.lock, type=LOG_TYPE_OPENED)
        response = self.client.get(reverse("machines:list"))
        listed = {m.pk: m for m in response.context["machines"]}
        self.assertEqual(listed[self.lock.pk].last_used, log.timestamp)

    def test_statistics_count_opened(self):
        AccessLog.objects.create(machine=self.lock, type=LOG_TYPE_OPENED)
        AccessLog.objects.create(machine=self.lock, type=LOG_TYPE_UNSUCCESSFUL)
        api = APIClient()
        authenticate(api, self.user)
        response = api.get(reverse("rest:v1:machine-statistics", kwargs={"pk": self.lock.pk}))
        self.assertEqual(response.status_code, 200)
        weekdays = response.json()["access_by_weekday"]
        self.assertEqual(sum(row["count"] for row in weekdays), 1)

    def test_access_log_shows_opened_badge(self):
        AccessLog.objects.create(machine=self.lock, type=LOG_TYPE_OPENED)
        response = self.client.get(reverse("access_log:list"))
        self.assertContains(response, 'data-lucide="lock-open"')
        self.assertContains(response, "Opened")
