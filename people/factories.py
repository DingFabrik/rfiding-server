import factory
from factory.django import DjangoModelFactory

from .models import Person, Qualification, Instructor, PERMISSION_LEVELS
from machines.models import Machine

class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person
        django_get_or_create = ('email',)

    name = factory.Faker("name")
    email = factory.Faker("email")
    member_id = factory.Sequence(lambda n: f"{n}")

class QualificationFactory(DjangoModelFactory):
    class Meta:
        model = Qualification

    person = factory.Iterator(Person.objects.all())
    machine = factory.Iterator(Machine.objects.all())
    permission_level = factory.Iterator([PERMISSION_LEVELS[0][0], PERMISSION_LEVELS[1][0], PERMISSION_LEVELS[2][0]])
    comment = factory.Faker("text")

class InstructorFactory(DjangoModelFactory):
    class Meta:
        model = Instructor

    person = factory.Iterator(Person.objects.all())
    machine = factory.Iterator(Machine.objects.all())