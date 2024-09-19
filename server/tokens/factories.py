import factory
from factory.django import DjangoModelFactory

from .models import Token
from people.models import Person


class TokenFactory(DjangoModelFactory):
    class Meta:
        model = Token

    serial = factory.Sequence(lambda n: f"{n}{n}{n}")
    person = factory.Iterator(Person.objects.all())
    purpose = factory.Sequence(lambda n: f"Label = {n}")
