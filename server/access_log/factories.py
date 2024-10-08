import factory
from factory.django import DjangoModelFactory

from .models import AccessLog, LOG_TYPES
from tokens.models import Token
from machines.models import Machine


class AccessLogFactory(DjangoModelFactory):
    class Meta:
        model = AccessLog

    token = factory.Iterator(Token.objects.all())
    machine = factory.Iterator(Machine.objects.all())
    type = factory.Iterator([x[0] for x in LOG_TYPES])
