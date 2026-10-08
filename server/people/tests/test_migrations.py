from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

BEFORE = ("people", "0021_person_detail_key_person_detail_key_expires_at")
DEDUPE = ("people", "0022_qualification_person_machine_unique")
BEFORE_BACKFILL = ("people", "0023_alter_qualification_is_instructor_and_more")
BACKFILL = ("people", "0024_backfill_qualification_last_used")


class MigrationTestCase(TransactionTestCase):
    def migrate(self, target):
        """Migrate `people` to `target` and every other app to its latest state."""
        executor = MigrationExecutor(connection)
        targets = [target] + [
            node for node in executor.loader.graph.leaf_nodes() if node[0] != target[0]
        ]
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


class DedupeQualificationsMigrationTests(MigrationTestCase):
    """0022 deletes duplicate qualifications before adding the unique constraint.

    It runs against production data once, so check that it keeps the newest
    qualification of each person/machine pair and leaves the rest untouched.
    """

    def test_keeps_newest_duplicate(self):
        apps = self.migrate(BEFORE)
        Person = apps.get_model("people", "Person")
        Machine = apps.get_model("machines", "Machine")
        Qualification = apps.get_model("people", "Qualification")

        alice = Person.objects.create(name="Alice", email="alice@example.com")
        bob = Person.objects.create(name="Bob", email="bob@example.com")
        lathe = Machine.objects.create(mac_address="aa:aa:aa:aa:aa:aa", hostname="lathe", name="Lathe")
        laser = Machine.objects.create(mac_address="bb:bb:bb:bb:bb:bb", hostname="laser", name="Laser")

        now = timezone.now()
        old = Qualification.objects.create(person=alice, machine=lathe, comment="old")
        new = Qualification.objects.create(person=alice, machine=lathe, comment="new")
        Qualification.objects.filter(pk=old.pk).update(created=now - timedelta(days=30))
        Qualification.objects.filter(pk=new.pk).update(created=now)
        other_machine = Qualification.objects.create(person=alice, machine=laser)
        other_person = Qualification.objects.create(person=bob, machine=lathe)

        apps = self.migrate(DEDUPE)
        Qualification = apps.get_model("people", "Qualification")

        self.assertEqual(
            set(Qualification.objects.values_list("pk", flat=True)),
            {new.pk, other_machine.pk, other_person.pk},
        )


class BackfillLastUsedMigrationTests(MigrationTestCase):
    """0024 fills Qualification.last_used from the access log, so qualifications
    used before last_used existed don't count as never used."""

    def setUp(self):
        apps = self.migrate(BEFORE_BACKFILL)
        self.Person = apps.get_model("people", "Person")
        self.Machine = apps.get_model("machines", "Machine")
        self.Token = apps.get_model("tokens", "Token")
        self.AccessLog = apps.get_model("access_log", "AccessLog")
        self.Qualification = apps.get_model("people", "Qualification")

        self.now = timezone.now()
        self.alice = self.Person.objects.create(name="Alice", email="alice@example.com")
        self.bob = self.Person.objects.create(name="Bob", email="bob@example.com")
        self.alice_token = self.Token.objects.create(serial="a1", person=self.alice)
        self.bob_token = self.Token.objects.create(serial="b1", person=self.bob)
        self.lathe = self.Machine.objects.create(
            mac_address="aa:aa:aa:aa:aa:aa", hostname="lathe", name="Lathe",
            qualification_expiry_used_days=30,
        )

    def log(self, machine, token, type="enabled", days_ago=0):
        log = self.AccessLog.objects.create(machine=machine, token=token, type=type)
        self.AccessLog.objects.filter(pk=log.pk).update(
            timestamp=self.now - timedelta(days=days_ago)
        )

    def qualify(self, person, machine, **fields):
        return self.Qualification.objects.create(person=person, machine=machine, **fields)

    def backfill(self, *qualifications):
        Qualification = self.migrate(BACKFILL).get_model("people", "Qualification")
        return [Qualification.objects.get(pk=q.pk) for q in qualifications]

    def test_uses_latest_successful_access(self):
        qualification = self.qualify(self.alice, self.lathe)
        self.log(self.lathe, self.alice_token, days_ago=10)
        self.log(self.lathe, self.alice_token, days_ago=3)
        self.log(self.lathe, self.alice_token, type="unsuccessful", days_ago=1)
        self.log(self.lathe, self.alice_token, type="disabled", days_ago=1)

        (qualification,) = self.backfill(qualification)

        self.assertEqual(qualification.last_used, self.now - timedelta(days=3))
        self.assertEqual(qualification.expires_at, self.now + timedelta(days=27))

    def test_ignores_other_people_machines_and_anonymized_logs(self):
        laser = self.Machine.objects.create(
            mac_address="bb:bb:bb:bb:bb:bb", hostname="laser", name="Laser"
        )
        qualification = self.qualify(self.alice, self.lathe)
        self.log(self.lathe, self.bob_token)
        self.log(laser, self.alice_token)
        self.log(self.lathe, None)

        (qualification,) = self.backfill(qualification)

        self.assertIsNone(qualification.last_used)

    def test_keeps_newer_last_used(self):
        recent = self.now - timedelta(hours=1)
        qualification = self.qualify(self.alice, self.lathe, last_used=recent)
        self.log(self.lathe, self.alice_token, days_ago=3)

        (qualification,) = self.backfill(qualification)

        self.assertEqual(qualification.last_used, recent)

    def test_compartment_uses_parent_locker_access(self):
        locker = self.Machine.objects.create(
            mac_address="cc:cc:cc:cc:cc:cc", hostname="locker", name="Locker", type="lock_group"
        )
        compartment = self.Machine.objects.create(
            mac_address="dd:dd:dd:dd:dd:dd", hostname="locker-1", name="Locker 1",
            type="compartment", parent=locker, compartment_id="1",
        )
        qualification = self.qualify(self.alice, compartment)
        self.log(locker, self.alice_token, days_ago=2)

        (qualification,) = self.backfill(qualification)

        self.assertEqual(qualification.last_used, self.now - timedelta(days=2))
        self.assertIsNone(qualification.expires_at)

    def test_expired_qualification_keeps_its_expiry(self):
        expires_at = self.now - timedelta(days=5)
        qualification = self.qualify(
            self.alice, self.lathe, expired=expires_at, expires_at=expires_at
        )
        self.log(self.lathe, self.alice_token, days_ago=40)

        (qualification,) = self.backfill(qualification)

        self.assertEqual(qualification.last_used, self.now - timedelta(days=40))
        self.assertEqual(qualification.expires_at, expires_at)
