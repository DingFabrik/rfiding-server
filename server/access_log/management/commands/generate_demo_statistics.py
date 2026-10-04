import math
import random
from contextlib import contextmanager
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from access_log.models import (
    AccessLog,
    LOG_TYPE_DISABLED,
    LOG_TYPE_ENABLED,
    LOG_TYPE_UNSUCCESSFUL,
)
from machines.models import Machine
from people.models import Person, Qualification
from space.models import SpaceState
from tokens.models import Token

DEMO_HOSTNAME_PREFIX = "demo-"
DEMO_EMAIL_DOMAIN = "demo.example.org"
DEMO_SERIAL_PREFIX = "DEMO"
# SpaceState has nothing to tag it with, so demo states get this microsecond value.
DEMO_SPACE_STATE_MICROSECOND = 424242

ACTIVE = Machine.MachineStatus.ACTIVE
INACTIVE = Machine.MachineStatus.INACTIVE
MAINTENANCE = Machine.MachineStatus.MAINTENANCE

# name, state, popularity weight, typical session length in minutes
MACHINES = [
    ("Laser Cutter", ACTIVE, 10, 45),
    ("3D Printer Prusa 1", ACTIVE, 8, 150),
    ("3D Printer Prusa 2", ACTIVE, 7, 150),
    ("Resin Printer", ACTIVE, 3, 120),
    ("CNC Router", ACTIVE, 4, 90),
    ("Lathe", ACTIVE, 3, 60),
    ("Milling Machine", ACTIVE, 2.5, 75),
    ("Table Saw", ACTIVE, 5, 20),
    ("Band Saw", ACTIVE, 4, 15),
    ("Drill Press", ACTIVE, 3.5, 10),
    ("Belt Sander", ACTIVE, 2, 10),
    ("Mitre Saw", ACTIVE, 2.5, 10),
    ("Sewing Machine", ACTIVE, 3, 60),
    ("Embroidery Machine", ACTIVE, 1.5, 90),
    ("Vinyl Cutter", ACTIVE, 2, 20),
    ("Soldering Station", ACTIVE, 4, 60),
    ("MIG Welder", ACTIVE, 1.5, 40),
    ("Plasma Cutter", ACTIVE, 0.8, 20),
    ("Vacuum Former", ACTIVE, 0.5, 15),
    ("Pottery Kiln", ACTIVE, 0.6, 240),
    ("Spray Booth", MAINTENANCE, 1, 30),
    # Never used, so they show up as idle / don't skew the rankings
    ("Thickness Planer", ACTIVE, 0, 15),
    ("Old Laser Cutter", INACTIVE, 0, 45),
]

# Qualification expiry (unused days, days after last use) for riskier machines
EXPIRING_MACHINES = {
    "Laser Cutter": (90, 180),
    "CNC Router": (90, 180),
    "Lathe": (90, 180),
    "Milling Machine": (90, 180),
    "Table Saw": (60, 120),
    "MIG Welder": (60, 120),
    "Plasma Cutter": (60, 120),
}

# Mon..Sun
WEEKDAY_FACTORS = [0.8, 1.0, 0.9, 1.1, 0.9, 1.5, 0.6]
WEEKDAY_HOURS = [0] * 8 + [1, 1, 2, 2, 2, 3, 3, 4, 5, 8, 10, 10, 9, 6, 3, 1]
SATURDAY_HOURS = [0] * 9 + [2, 5, 8, 9, 10, 10, 9, 8, 6, 4, 3, 2, 1, 0, 0]
SUNDAY_HOURS = [0] * 11 + [2, 4, 6, 7, 7, 6, 4, 2, 1, 0, 0, 0, 0]
SESSIONS_PER_MEMBER_PER_DAY = 0.3
UNSUCCESSFUL_RATE = 0.04
MAX_SESSION_MINUTES = 8 * 60
# Opening hours per weekday (Mon..Sun) and how many sessions still happen on closed days
OPENING_HOURS = [(14, 23)] * 5 + [(10, 21), (12, 20)]
CLOSED_DAY_RATE = 0.05
CLOSED_DAY_FACTOR = 0.1


@contextmanager
def explicit_timestamps(*models):
    """Let bulk_create keep the `created`/`timestamp` values we set ourselves."""
    fields = [
        field
        for model in models
        for field in model._meta.concrete_fields
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False)
    ]
    saved = [(field, field.auto_now, field.auto_now_add) for field in fields]
    for field in fields:
        field.auto_now = field.auto_now_add = False
    try:
        yield
    finally:
        for field, auto_now, auto_now_add in saved:
            field.auto_now, field.auto_now_add = auto_now, auto_now_add


def poisson(rng, lam):
    threshold, count, product = math.exp(-lam), 0, rng.random()
    while product > threshold:
        count += 1
        product *= rng.random()
    return count


def season_factor(date):
    # Quieter in the summer holidays and around Christmas.
    if date.month in (7, 8):
        return 0.7
    if (date.month == 12 and date.day >= 20) or (date.month == 1 and date.day <= 6):
        return 0.4
    return 1.0


class Command(BaseCommand):
    help = (
        "Adds demo machines, people, qualifications and two years of access logs for "
        "the statistics page. Existing data is left untouched."
    )

    def add_arguments(self, parser):
        parser.add_argument("--people", type=int, default=80)
        parser.add_argument("--days", type=int, default=730)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove previously generated demo data before generating new data.",
        )

    def handle(self, *args, people, days, seed, clear, **options):
        demo_machines = Machine.objects.filter(hostname__startswith=DEMO_HOSTNAME_PREFIX)
        demo_people = Person.objects.filter(email__endswith=f"@{DEMO_EMAIL_DOMAIN}")
        if clear:
            # Access logs, qualifications and tokens cascade.
            demo_machines.delete()
            demo_people.delete()
            SpaceState.objects.filter(pk__in=self.demo_space_state_ids()).delete()
        elif demo_machines.exists() or demo_people.exists():
            raise CommandError("Demo data already exists. Use --clear to regenerate it.")

        self.rng = random.Random(seed)
        self.now = timezone.now()
        with transaction.atomic(), explicit_timestamps(
            Machine, Person, Token, Qualification, AccessLog, SpaceState
        ):
            opening_hours = self.create_space_states(days)
            machines = self.create_machines(days)
            members = self.create_people(people, days)
            qualifications = self.create_qualifications(members, machines)
            logs = self.create_access_logs(members, machines, days, opening_hours)
            self.mark_qualifications(qualifications, logs)
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(machines)} machines, {len(members)} people, "
                f"{len(qualifications)} qualifications, {len(logs)} access logs "
                f"and opening hours for {len(opening_hours)} days."
            )
        )

    def demo_space_state_ids(self):
        return [
            pk
            for pk, created in SpaceState.objects.values_list("pk", "created")
            if created.microsecond == DEMO_SPACE_STATE_MICROSECOND
        ]

    def create_space_states(self, days):
        """Opening hours for the demo timeframe, as {date: (opened, closed)}."""
        today = timezone.localdate()
        first_day = today - timedelta(days=days)
        window_start = timezone.make_aware(datetime.combine(first_day, time.min))
        demo_ids = set(self.demo_space_state_ids())
        if SpaceState.objects.filter(created__gte=window_start).exclude(pk__in=demo_ids).exists():
            self.stdout.write(
                self.style.WARNING("Real space states exist in the demo timeframe, not generating opening hours.")
            )
            return {}

        def at(date, hour, jitter_minutes):
            moment = timezone.make_aware(datetime.combine(date, time(hour)))
            moment += timedelta(minutes=self.rng.uniform(*jitter_minutes))
            return moment.replace(microsecond=DEMO_SPACE_STATE_MICROSECOND)

        opening_hours = {}
        states = []
        for offset in range(days, -1, -1):
            date = today - timedelta(days=offset)
            christmas = (date.month == 12 and date.day >= 24) or (date.month == 1 and date.day == 1)
            if christmas or self.rng.random() < CLOSED_DAY_RATE:
                continue
            open_hour, close_hour = OPENING_HOURS[date.weekday()]
            opened = at(date, open_hour, (-30, 30))
            closed = at(date, close_hour, (-30, 60))
            if opened > self.now:
                break
            opening_hours[date] = (opened, closed)
            states.append(SpaceState(is_open=True, created=opened, updated=opened))
            if closed <= self.now:
                states.append(SpaceState(is_open=False, created=closed, updated=closed))
        SpaceState.objects.bulk_create(states)
        return opening_hours

    def create_machines(self, days):
        created = self.now - timedelta(days=days + 30)
        machines = Machine.objects.bulk_create(
            Machine(
                name=name,
                state=state,
                hostname=f"{DEMO_HOSTNAME_PREFIX}{index}",
                qualification_expiry_unused_days=EXPIRING_MACHINES.get(name, (None, None))[0],
                qualification_expiry_used_days=EXPIRING_MACHINES.get(name, (None, None))[1],
                created=created,
                updated=created,
            )
            for index, (name, state, _, _) in enumerate(MACHINES)
        )
        for machine, (_, _, weight, minutes) in zip(machines, MACHINES):
            machine.demo_weight = weight
            machine.demo_minutes = minutes
        return machines

    def create_people(self, count, days):
        fake = Faker()
        fake.seed_instance(self.rng.randrange(2**32))
        members = []
        for index in range(count):
            # More recent joins than old ones, so usage grows over time.
            joined = self.now - timedelta(days=(days + 60) * self.rng.random() ** 0.7)
            left = None
            if self.rng.random() < 0.15:
                left = joined + timedelta(days=self.rng.uniform(30, days))
                if left >= self.now:
                    left = None
            person = Person(
                name=fake.name(),
                email=f"member{index}@{DEMO_EMAIL_DOMAIN}",
                is_active=left is None,
                created=joined,
                updated=joined,
            )
            person.demo_joined = joined
            person.demo_left = left
            # A few power users, many occasional visitors.
            person.demo_activity = min(self.rng.paretovariate(1.5), 6)
            members.append(person)
        Person.objects.bulk_create(members)
        Token.objects.bulk_create(
            Token(
                serial=f"{DEMO_SERIAL_PREFIX}{index:05d}",
                person=person,
                purpose="Demo",
                created=person.demo_joined,
                updated=person.demo_joined,
            )
            for index, person in enumerate(members)
        )
        tokens = {token.person_id: token for token in Token.objects.filter(person__in=members)}
        for person in members:
            person.demo_token = tokens[person.pk]
        return members

    def create_qualifications(self, members, machines):
        usable = [machine for machine in machines if machine.demo_weight > 0]
        qualifications = []
        for person in members:
            count = min(len(usable), 1 + int(person.demo_activity * self.rng.uniform(1, 3)))
            chosen = set()
            while len(chosen) < count:
                chosen.add(self.rng.choices(usable, weights=[m.demo_weight for m in usable])[0])
            person.demo_machines = []
            for machine in chosen:
                granted = person.demo_joined + timedelta(days=self.rng.expovariate(1 / 30))
                if granted >= self.now:
                    continue
                qualification = Qualification(
                    person=person,
                    machine=machine,
                    permission_level="if_space_open",
                    created=granted,
                    updated=granted,
                )
                qualification.demo_granted = granted
                # Most people mainly use a few of the machines they're qualified on.
                qualification.demo_interest = self.rng.random() ** 3
                qualifications.append(qualification)
                person.demo_machines.append(qualification)
        return Qualification.objects.bulk_create(qualifications)

    def pick_time(self, date):
        weekday = date.weekday()
        hours = SATURDAY_HOURS if weekday == 5 else SUNDAY_HOURS if weekday == 6 else WEEKDAY_HOURS
        hour = self.rng.choices(range(24), weights=hours)[0]
        moment = datetime.combine(date, time(hour, self.rng.randrange(60)))
        return timezone.make_aware(moment) if timezone.is_naive(moment) else moment

    def create_access_logs(self, members, machines, days, opening_hours):
        usable = [machine for machine in machines if machine.demo_weight > 0]
        logs = []
        today = timezone.localdate()
        for offset in range(days, -1, -1):
            date = today - timedelta(days=offset)
            day_start = timezone.make_aware(datetime.combine(date, time.min))
            present = [
                person
                for person in members
                if person.demo_joined <= day_start
                and (person.demo_left is None or person.demo_left > day_start)
            ]
            if not present:
                continue
            rate = (
                len(present)
                * SESSIONS_PER_MEMBER_PER_DAY
                * WEEKDAY_FACTORS[date.weekday()]
                * season_factor(date)
            )
            if opening_hours and date not in opening_hours:
                rate *= CLOSED_DAY_FACTOR
            weights = [person.demo_activity for person in present]
            for _ in range(poisson(self.rng, rate)):
                start = self.pick_time(date)
                if start > self.now:
                    continue
                person = self.rng.choices(present, weights=weights)[0]
                token = person.demo_token
                held = [q for q in person.demo_machines if q.demo_granted <= start]
                allowed = [q.machine for q in held]
                if not allowed or self.rng.random() < UNSUCCESSFUL_RATE:
                    machine = self.rng.choices(usable, weights=[m.demo_weight for m in usable])[0]
                    if machine not in allowed:
                        logs.append(AccessLog(machine=machine, token=token, type=LOG_TYPE_UNSUCCESSFUL, timestamp=start))
                        continue
                machine = self.rng.choices(
                    allowed, weights=[q.machine.demo_weight * q.demo_interest for q in held]
                )[0]
                logs.append(AccessLog(machine=machine, token=token, type=LOG_TYPE_ENABLED, timestamp=start))
                minutes = min(
                    MAX_SESSION_MINUTES,
                    self.rng.lognormvariate(math.log(machine.demo_minutes), 0.5),
                )
                end = start + timedelta(minutes=minutes)
                if end <= self.now:
                    logs.append(
                        AccessLog(
                            machine=machine,
                            token=token,
                            type=LOG_TYPE_DISABLED,
                            timestamp=end,
                            enabled_duration=end - start,
                        )
                    )
        return AccessLog.objects.bulk_create(logs, batch_size=2000)

    def mark_qualifications(self, qualifications, logs):
        last_used = {}
        for log in logs:
            if log.type == LOG_TYPE_ENABLED:
                key = (log.token.person_id, log.machine_id)
                last_used[key] = max(last_used.get(key, log.timestamp), log.timestamp)
        for qualification in qualifications:
            qualification.last_used = last_used.get((qualification.person_id, qualification.machine_id))
            qualification.expires_at = qualification.compute_expires_at()
            expiries = [qualification.expires_at]
            if qualification.person.demo_left is not None:
                expiries.append(qualification.person.demo_left + timedelta(days=180))
            expiries = [expiry for expiry in expiries if expiry is not None and expiry < self.now]
            if expiries:
                qualification.expired = min(expiries)
        Qualification.objects.bulk_update(
            qualifications, ["last_used", "expires_at", "expired"], batch_size=2000
        )
