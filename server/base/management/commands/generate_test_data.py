from django.db import transaction
from django.core.management.base import BaseCommand

from people.models import Person, Qualification
from machines.models import Machine
from tokens.models import Token

from people.factories import PersonFactory, QualificationFactory
from machines.factories import MachineFactory
from tokens.factories import TokenFactory
from access_log.factories import AccessLogFactory

NUM_MACHINES = 60
NUM_PEOPLE = 50
NUM_LOGS = 100


class Command(BaseCommand):
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        models = [Machine, Person, Token, Qualification]
        for m in models:
            m.objects.all().delete()

        self.stdout.write("Creating new data...")
        MachineFactory.create_batch(NUM_MACHINES)
        PersonFactory.create_batch(NUM_PEOPLE)
        TokenFactory.create_batch(NUM_PEOPLE)
        QualificationFactory.create_batch(NUM_PEOPLE * NUM_MACHINES)
        AccessLogFactory.create_batch(NUM_LOGS)
