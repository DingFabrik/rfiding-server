import factory
from factory.django import DjangoModelFactory

from .models import Machine


class MachineFactory(DjangoModelFactory):
    class Meta:
        model = Machine

    name = factory.Sequence(lambda n: f"Machine {n}")
    hostname = factory.Sequence(lambda n: f"machine{n}")
    mac_address = factory.Faker("mac_address")
    is_active = True
    completed_setup = True
